from datetime import date
import sqlite3

from src.infraestrutura.banco import conectar
from src.financeiro.parcelas import calcular_data_vencimento


def sincronizar_status_residentes(data_referencia=None):
    """Ativa somente residentes com internação dentro do período contratado."""
    referencia = date.fromisoformat(data_referencia) if data_referencia else date.today()
    conexao = conectar()
    try:
        internacoes = conexao.execute(
            "SELECT id,residente_id,data_acolhimento,periodo_tratamento,encerrada_em,modalidade FROM internacoes WHERE status!='CANCELADA'"
        ).fetchall()
        ativas = set()
        for internacao_id, residente_id, inicio, periodo, encerrada_em, modalidade in internacoes:
            inicio_data = date.fromisoformat(inicio)
            if modalidade == "VOLUNTARIO":
                dentro_periodo = inicio_data <= referencia
            else:
                fim = calcular_data_vencimento(inicio, int(periodo))
                dentro_periodo = inicio_data <= referencia <= fim
            if encerrada_em and date.fromisoformat(encerrada_em) <= referencia:
                status = "ENCERRADA"
            elif referencia < inicio_data:
                status = "AGENDADA"
            else:
                status = "ATIVA" if dentro_periodo else "ENCERRADA"
            conexao.execute("UPDATE internacoes SET status=? WHERE id=?", (status, internacao_id))
            if status == "ATIVA":
                ativas.add(residente_id)
        conexao.execute("UPDATE residentes SET ativo=0")
        if ativas:
            marcadores = ",".join("?" for _ in ativas)
            conexao.execute(f"UPDATE residentes SET ativo=1 WHERE id IN ({marcadores})", tuple(ativas))
        conexao.commit()
        return {"ativos": len(ativas), "data_referencia": referencia.isoformat()}
    finally:
        conexao.close()


def cadastrar_internacao(
    residente_id,
    responsavel_id,
    data_acolhimento,
    periodo_tratamento,
    valor_contrato,
    valor_acolhimento,
    valor_mensalidade,
    modalidade="PARTICULAR",
    convenio_id=None,
    servicos_voluntario=None,
    conexao=None,
):
    modalidade = str(modalidade or "PARTICULAR").strip().upper()
    modalidades = {"PARTICULAR", "SOCIAL", "CONVENIO", "VOLUNTARIO"}
    if modalidade not in modalidades:
        return {"sucesso": False, "erro": "Modalidade de residência inválida."}
    try:
        periodo_tratamento = 0 if modalidade == "VOLUNTARIO" else int(periodo_tratamento)
        date.fromisoformat(data_acolhimento)
        valores = [int(valor_contrato), int(valor_acolhimento), int(valor_mensalidade)]
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Os dados da internação são inválidos."}
    if modalidade != "VOLUNTARIO" and periodo_tratamento <= 0:
        return {"sucesso": False, "erro": "O período de tratamento deve ser maior que zero."}
    if any(valor < 0 for valor in valores):
        return {"sucesso": False, "erro": "Os valores da internação não podem ser negativos."}
    if modalidade == "PARTICULAR" and valores[0] != valores[1] + valores[2] * periodo_tratamento:
        return {"sucesso": False, "erro": "O contrato deve corresponder ao acolhimento mais as mensalidades do período."}

    conexao_propria = conexao is None
    conexao = conexao or conectar()
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()

    # Verifica se o residente existe
    cursor.execute(
        "SELECT id FROM residentes WHERE id = ?",
        (residente_id,)
    )

    if cursor.fetchone() is None:
        if conexao_propria:
            conexao.close()
        return {
            "sucesso": False,
            "erro": "Residente não encontrado."
        }

    # Verifica se o responsável existe
    cursor.execute(
        "SELECT id,ativo FROM responsaveis WHERE id = ?",
        (responsavel_id,)
    )

    responsavel = cursor.fetchone()
    if responsavel is None:
        if conexao_propria:
            conexao.close()
        return {
            "sucesso": False,
            "erro": "Responsável não encontrado."
        }
    if not responsavel["ativo"]:
        if conexao_propria:
            conexao.close()
        return {"sucesso": False, "erro": "O responsável selecionado está inativo."}

    valor_diaria = 0
    if modalidade == "CONVENIO":
        convenio = cursor.execute(
            "SELECT id,valor_diaria,ativo FROM convenios WHERE id=?", (convenio_id,)
        ).fetchone()
        if not convenio or not convenio["ativo"]:
            if conexao_propria:
                conexao.close()
            return {"sucesso": False, "erro": "Selecione um convênio ativo."}
        valor_diaria = convenio["valor_diaria"]
        valores = [0, 0, 0]
    elif modalidade in ("SOCIAL", "VOLUNTARIO"):
        valores = [0, 0, 0]
        convenio_id = None
    else:
        convenio_id = None
    servicos_voluntario = str(servicos_voluntario or "").strip() or None
    if modalidade == "VOLUNTARIO" and not servicos_voluntario:
        if conexao_propria:
            conexao.close()
        return {"sucesso": False, "erro": "Informe os serviços que serão prestados pelo voluntário."}

    inicio_novo = date.fromisoformat(data_acolhimento)
    fim_novo = date.max if modalidade == "VOLUNTARIO" else calcular_data_vencimento(data_acolhimento, periodo_tratamento)
    for existente in cursor.execute(
        """SELECT id,data_acolhimento,periodo_tratamento,encerrada_em,modalidade
           FROM internacoes WHERE residente_id=? AND status!='CANCELADA'""", (residente_id,)
    ).fetchall():
        inicio_existente = date.fromisoformat(existente["data_acolhimento"])
        if existente["encerrada_em"]:
            fim_existente = date.fromisoformat(existente["encerrada_em"])
        elif existente["modalidade"] == "VOLUNTARIO":
            fim_existente = date.max
        else:
            fim_existente = calcular_data_vencimento(
                existente["data_acolhimento"], existente["periodo_tratamento"]
            )
        if inicio_novo <= fim_existente and inicio_existente <= fim_novo:
            if conexao_propria:
                conexao.close()
            return {"sucesso": False, "erro": f"O residente já possui a internação {existente['id']} em período coincidente."}

    # Cria a internação
    cursor.execute(
        """
        INSERT INTO internacoes (
            residente_id,
            responsavel_id,
            data_acolhimento,
            periodo_tratamento,
            valor_contrato,
            valor_acolhimento,
            valor_mensalidade,
            modalidade,
            convenio_id,
            valor_diaria,
            servicos_voluntario
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            residente_id,
            responsavel_id,
            data_acolhimento,
            periodo_tratamento,
            valores[0], valores[1], valores[2], modalidade, convenio_id,
            valor_diaria, servicos_voluntario
        )
    )

    internacao_id = cursor.lastrowid

    cursor.execute(
        """INSERT INTO residente_responsavel (residente_id,responsavel_id,relacao,principal)
           VALUES (?,?,?,1)
           ON CONFLICT(residente_id,responsavel_id) DO UPDATE SET principal=1""",
        (residente_id, responsavel_id, "Responsável pela internação"),
    )

    if conexao_propria:
        conexao.commit()
        conexao.close()
        sincronizar_status_residentes()

    return {
        "sucesso": True,
        "id": internacao_id
    }


def cadastrar_internacao_com_cobrancas(*args, **kwargs):
    """Grava internação, vínculo e cobranças em uma única transação."""
    from src.financeiro.cobrancas import gerar_cobrancas
    conexao = conectar()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        resultado = cadastrar_internacao(*args, **kwargs, conexao=conexao)
        if not resultado.get("sucesso"):
            conexao.rollback()
            return resultado
        cobrancas = gerar_cobrancas(resultado["id"], conexao=conexao)
        if not cobrancas.get("sucesso"):
            raise RuntimeError(cobrancas.get("erro") or "Não foi possível gerar as cobranças.")
        conexao.commit()
        resultado["cobrancas"] = cobrancas.get("quantidade", 0)
    except Exception as erro:
        conexao.rollback()
        return {"sucesso": False, "erro": f"A internação não foi gravada: {erro}"}
    finally:
        conexao.close()
    sincronizar_status_residentes()
    return resultado


def buscar_internacao(internacao_id):
    sincronizar_status_residentes()
    conexao = conectar()
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            i.id,
            i.residente_id,
            r.nome AS residente_nome,
            i.responsavel_id,
            rp.nome AS responsavel_nome,
            i.data_acolhimento,
            i.periodo_tratamento,
            i.valor_contrato,
            i.valor_acolhimento,
            i.valor_mensalidade,
            i.status,i.modalidade,i.convenio_id,c.nome AS convenio_nome,
            i.valor_diaria,i.servicos_voluntario
        FROM internacoes i
        INNER JOIN residentes r
            ON r.id = i.residente_id
        INNER JOIN responsaveis rp
            ON rp.id = i.responsavel_id
        LEFT JOIN convenios c ON c.id=i.convenio_id
        WHERE i.id = ?
        """,
        (internacao_id,)
    )

    resultado = cursor.fetchone()

    conexao.close()

    if resultado is None:
        return None

    return dict(resultado)


def encerrar_internacao(internacao_id, data_encerramento=None, motivo=None,
                       autorizar_ajuste_desconto=False):
    data_encerramento = data_encerramento or date.today().isoformat()
    motivo = str(motivo or "Encerramento antecipado").strip()
    try:
        encerramento = date.fromisoformat(data_encerramento)
        if encerramento.isoformat() != data_encerramento or encerramento > date.today():
            raise ValueError
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Data de encerramento inválida ou futura."}
    conexao = conectar()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        internacao = conexao.execute(
            "SELECT data_acolhimento,encerrada_em,periodo_tratamento,modalidade FROM internacoes WHERE id=?", (internacao_id,)
        ).fetchone()
        if not internacao:
            return {"sucesso": False, "erro": "Internação não encontrada."}
        if internacao[1]:
            return {"sucesso": False, "erro": "A internação já foi encerrada antecipadamente."}
        if data_encerramento < internacao[0]:
            return {"sucesso": False, "erro": "O encerramento não pode ser anterior ao acolhimento."}
        if internacao[3] != "VOLUNTARIO" and encerramento > calcular_data_vencimento(internacao[0], internacao[2]):
            return {"sucesso": False, "erro": "O encerramento não pode ultrapassar o período contratado."}
        from src.financeiro.cobrancas import ajustar_convenio_ao_encerrar
        ajustar_convenio_ao_encerrar(internacao_id, data_encerramento, conexao,
                                    autorizar_ajuste_desconto)
        conexao.execute(
            "UPDATE internacoes SET status='ENCERRADA',encerrada_em=?,motivo_encerramento=? WHERE id=?",
            (data_encerramento, motivo, internacao_id),
        )
        conexao.commit()
    except ValueError as erro:
        conexao.rollback()
        return {"sucesso": False, "erro": str(erro)}
    finally:
        conexao.close()
    sincronizar_status_residentes()
    return {"sucesso": True, "id": internacao_id, "status": "ENCERRADA", "encerrada_em": data_encerramento}


def alterar_responsavel_principal(internacao_id, responsavel_id):
    conexao = conectar()
    try:
        internacao = conexao.execute(
            "SELECT residente_id FROM internacoes WHERE id=?", (internacao_id,)
        ).fetchone()
        if not internacao:
            return {"sucesso": False, "erro": "Internação não encontrada."}
        responsavel = conexao.execute(
            "SELECT id,ativo FROM responsaveis WHERE id=?", (responsavel_id,)
        ).fetchone()
        if not responsavel:
            return {"sucesso": False, "erro": "Responsável não encontrado."}
        if not responsavel[1]:
            return {"sucesso": False, "erro": "O responsável está inativo."}
        residente_id = internacao[0]
        conexao.execute("BEGIN")
        conexao.execute("UPDATE internacoes SET responsavel_id=? WHERE id=?", (responsavel_id, internacao_id))
        conexao.execute("UPDATE residente_responsavel SET principal=0 WHERE residente_id=?", (residente_id,))
        conexao.execute(
            """INSERT INTO residente_responsavel(residente_id,responsavel_id,relacao,principal)
               VALUES(?,?,?,1) ON CONFLICT(residente_id,responsavel_id)
               DO UPDATE SET principal=1""",
            (residente_id, responsavel_id, "Responsável principal"),
        )
        conexao.commit()
        return {"sucesso": True, "id": internacao_id, "responsavel_id": responsavel_id}
    finally:
        conexao.close()


def cancelar_agendamento(internacao_id, motivo=None):
    """Cancela somente acolhimentos futuros sem recebimentos efetivos."""
    conexao = conectar()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        registro = conexao.execute(
            "SELECT data_acolhimento,status FROM internacoes WHERE id=?", (internacao_id,)
        ).fetchone()
        if not registro or registro[1] == "CANCELADA" or registro[0] <= date.today().isoformat():
            return {"sucesso": False, "erro": "Somente agendamentos futuros podem ser cancelados."}
        if conexao.execute(
            "SELECT 1 FROM recebimentos r JOIN cobrancas c ON c.id=r.cobranca_id WHERE c.internacao_id=? LIMIT 1",
            (internacao_id,),
        ).fetchone():
            return {"sucesso": False, "erro": "Faça o acerto dos recebimentos antes de cancelar o agendamento."}
        motivo = str(motivo or "Cancelamento de agendamento").strip()
        conexao.execute(
            """INSERT INTO ajustes_cobrancas(cobranca_id,valor_anterior,valor_novo,
               desconto_anterior,desconto_novo,motivo)
               SELECT id,valor,0,desconto,0,? FROM cobrancas WHERE internacao_id=?""",
            (motivo, internacao_id),
        )
        conexao.execute("UPDATE cobrancas SET valor=0,desconto=0,status='DESCONTADA' WHERE internacao_id=?", (internacao_id,))
        conexao.execute("UPDATE internacoes SET status='CANCELADA',motivo_encerramento=? WHERE id=?", (motivo, internacao_id))
        conexao.commit()
    finally:
        conexao.close()
    sincronizar_status_residentes()
    return {"sucesso": True, "id": internacao_id, "status": "CANCELADA"}

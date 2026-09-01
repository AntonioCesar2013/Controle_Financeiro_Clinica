from datetime import date
import sqlite3

from src.banco import conectar
from src.parcelas import calcular_data_vencimento


def sincronizar_status_residentes(data_referencia=None):
    """Ativa somente residentes com internação dentro do período contratado."""
    referencia = date.fromisoformat(data_referencia) if data_referencia else date.today()
    conexao = conectar()
    try:
        internacoes = conexao.execute(
            "SELECT id,residente_id,data_acolhimento,periodo_tratamento,encerrada_em FROM internacoes"
        ).fetchall()
        ativas = set()
        for internacao_id, residente_id, inicio, periodo, encerrada_em in internacoes:
            inicio_data = date.fromisoformat(inicio)
            fim = calcular_data_vencimento(inicio, int(periodo))
            status = "ATIVA" if not encerrada_em and inicio_data <= referencia <= fim else "ENCERRADA"
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
    valor_mensalidade
):
    try:
        periodo_tratamento = int(periodo_tratamento)
        date.fromisoformat(data_acolhimento)
        valores = [int(valor_contrato), int(valor_acolhimento), int(valor_mensalidade)]
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Os dados da internação são inválidos."}
    if periodo_tratamento <= 0:
        return {"sucesso": False, "erro": "O período de tratamento deve ser maior que zero."}
    if any(valor < 0 for valor in valores):
        return {"sucesso": False, "erro": "Os valores da internação não podem ser negativos."}

    conexao = conectar()
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    # Verifica se o residente existe
    cursor.execute(
        "SELECT id FROM residentes WHERE id = ?",
        (residente_id,)
    )

    if cursor.fetchone() is None:
        conexao.close()
        return {
            "sucesso": False,
            "erro": "Residente não encontrado."
        }

    # Verifica se o responsável existe
    cursor.execute(
        "SELECT id FROM responsaveis WHERE id = ?",
        (responsavel_id,)
    )

    if cursor.fetchone() is None:
        conexao.close()
        return {
            "sucesso": False,
            "erro": "Responsável não encontrado."
        }

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
            valor_mensalidade
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            residente_id,
            responsavel_id,
            data_acolhimento,
            periodo_tratamento,
            valor_contrato,
            valor_acolhimento,
            valor_mensalidade
        )
    )

    internacao_id = cursor.lastrowid

    cursor.execute(
        """INSERT INTO residente_responsavel (residente_id,responsavel_id,relacao,principal)
           VALUES (?,?,?,1)
           ON CONFLICT(residente_id,responsavel_id) DO UPDATE SET principal=1""",
        (residente_id, responsavel_id, "Responsável pela internação"),
    )

    conexao.commit()
    conexao.close()

    sincronizar_status_residentes()

    return {
        "sucesso": True,
        "id": internacao_id
    }


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
            i.status
        FROM internacoes i
        INNER JOIN residentes r
            ON r.id = i.residente_id
        INNER JOIN responsaveis rp
            ON rp.id = i.responsavel_id
        WHERE i.id = ?
        """,
        (internacao_id,)
    )

    resultado = cursor.fetchone()

    conexao.close()

    if resultado is None:
        return None

    return dict(resultado)


def encerrar_internacao(internacao_id, data_encerramento=None, motivo=None):
    data_encerramento = data_encerramento or date.today().isoformat()
    motivo = str(motivo or "Encerramento antecipado").strip()
    try:
        date.fromisoformat(data_encerramento)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Data de encerramento inválida."}
    conexao = conectar()
    try:
        internacao = conexao.execute(
            "SELECT data_acolhimento,encerrada_em FROM internacoes WHERE id=?", (internacao_id,)
        ).fetchone()
        if not internacao:
            return {"sucesso": False, "erro": "Internação não encontrada."}
        if internacao[1]:
            return {"sucesso": False, "erro": "A internação já foi encerrada antecipadamente."}
        if data_encerramento < internacao[0]:
            return {"sucesso": False, "erro": "O encerramento não pode ser anterior ao acolhimento."}
        conexao.execute(
            "UPDATE internacoes SET status='ENCERRADA',encerrada_em=?,motivo_encerramento=? WHERE id=?",
            (data_encerramento, motivo, internacao_id),
        )
        conexao.commit()
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

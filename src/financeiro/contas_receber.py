
"""Motor de consulta de contas a receber.

Consolida cobranças (o que deveria ser recebido) com recebimentos (o que
entrou), sem alterar dados persistidos, vencimentos ou status financeiro.
"""

from datetime import date
import sqlite3

from src.infraestrutura.banco import conectar
from src.financeiro.parcelas import calcular_status_parcela
from src.financeiro.regras_financeiras import (
    calcular_saldo_restante,
    calcular_valor_devido,
)


def _situacao_temporal(cobranca, data_referencia=None):
    """Calcula a situação temporal sem substituir o status financeiro salvo.

    Uma cobrança parcial mantém o estado financeiro e pode estar atrasada.
    """
    status_financeiro = cobranca["status"]

    if status_financeiro in ("ABERTA", "PARCIAL"):
        return calcular_status_parcela(
            cobranca["data_vencimento"],
            data_referencia=data_referencia,
        )

    if status_financeiro == "PAGA" and cobranca["data_pagamento"]:
        return calcular_status_parcela(
            cobranca["data_vencimento"],
            data_pagamento=cobranca["data_pagamento"],
            data_referencia=data_referencia,
        )

    return None


def _paga_em_atraso(status, data_vencimento, data_pagamento):
    """Indica quitação após o vencimento apenas quando a cobrança está paga."""
    if status != "PAGA" or data_pagamento is None:
        return None

    vencimento = date.fromisoformat(data_vencimento)
    pagamento = date.fromisoformat(data_pagamento)
    return pagamento > vencimento


def consolidar_cobranca(cobranca, data_referencia=None):
    """Acrescenta campos derivados à cobrança sem alterar os valores originais."""
    total_recebido = cobranca["total_recebido"]
    valor = cobranca["valor"]
    desconto = cobranca["desconto"]

    valor_devido = calcular_valor_devido(valor, desconto)
    saldo_restante = calcular_saldo_restante(
        valor_devido,
        total_recebido,
    )

    return {
        "id": cobranca["id"],
        "internacao_id": cobranca["internacao_id"],
        "residente_nome": cobranca.get("residente_nome"),
        "descricao": cobranca.get("descricao"),
        "origem_nome": cobranca.get("residente_nome") or cobranca.get("descricao"),
        "responsavel_nome": cobranca.get("responsavel_nome"),
        "residente_id": cobranca.get("residente_id"),
        "modalidade": cobranca.get("modalidade"),
        "convenio_nome": cobranca.get("convenio_nome"),
        "numero_parcela": cobranca["numero_parcela"],
        "tipo": cobranca["tipo"],
        "data_vencimento": cobranca["data_vencimento"],
        "valor": valor,
        "desconto": desconto,
        "status": cobranca["status"],
        "valor_devido": valor_devido,
        "total_recebido": total_recebido,
        "total_multa_juros": cobranca.get("total_multa_juros", 0),
        "total_recebido_com_encargos": cobranca.get("total_recebido_com_encargos", total_recebido),
        "saldo_restante": saldo_restante,
        "data_pagamento": cobranca["data_pagamento"],
        "situacao_temporal": _situacao_temporal(cobranca, data_referencia),
        "paga_em_atraso": _paga_em_atraso(
            cobranca["status"],
            cobranca["data_vencimento"],
            cobranca["data_pagamento"],
        ),
        "dias_atraso": max(0, ((date.fromisoformat(data_referencia) if isinstance(data_referencia, str)
                               else data_referencia or date.today()) - date.fromisoformat(cobranca["data_vencimento"])).days)
                       if saldo_restante > 0 else 0,
    }


def _consultar_cobrancas(cobranca_id=None, internacao_id=None, tipo=None, busca=None,
                         limite=None, deslocamento=0):
    conexao = conectar()
    cursor = conexao.cursor()

    filtros = []
    parametros = []

    if cobranca_id is not None:
        filtros.append("c.id = ?")
        parametros.append(cobranca_id)

    if internacao_id is not None:
        filtros.append("c.internacao_id = ?")
        parametros.append(internacao_id)

    if tipo is not None:
        filtros.append("c.tipo = ?")
        parametros.append(tipo)

    if busca:
        filtros.append("(res.nome LIKE ? OR c.descricao LIKE ?)")
        termo = f"%{busca.strip()}%"
        parametros.extend((termo, termo))

    where = " WHERE " + " AND ".join(filtros) if filtros else ""

    paginacao = " LIMIT ? OFFSET ?" if limite is not None else ""
    parametros_consulta = [*parametros, *([limite, deslocamento] if limite is not None else [])]
    cobrancas = cursor.execute(
        f"""
        SELECT
            c.id,
            c.internacao_id,
            c.numero_parcela,
            c.tipo,
            c.descricao,
            c.data_vencimento,
            c.valor,
            c.desconto,
            c.status,
            COALESCE(SUM(r.valor), 0) AS total_recebido,
            COALESCE(SUM(r.multa_juros), 0) AS total_multa_juros,
            MAX(CASE WHEN r.valor > 0 THEN r.data_recebimento END) AS data_pagamento,
            res.nome AS residente_nome, rp.nome AS responsavel_nome,
            res.id AS residente_id, i.modalidade, cv.nome AS convenio_nome
        FROM cobrancas c
        LEFT JOIN internacoes i ON i.id=c.internacao_id
        LEFT JOIN residentes res ON res.id=i.residente_id
        LEFT JOIN responsaveis rp ON rp.id=i.responsavel_id
        LEFT JOIN convenios cv ON cv.id=i.convenio_id
        LEFT JOIN recebimentos_liquidos r
            ON r.cobranca_id = c.id
        {where}
        GROUP BY c.id
        ORDER BY c.data_vencimento, c.id
        {paginacao}
        """,
        parametros_consulta,
    ).fetchall()

    conexao.close()

    return [
        {
            "id": cobranca[0],
            "internacao_id": cobranca[1],
            "numero_parcela": cobranca[2],
            "tipo": cobranca[3],
            "descricao": cobranca[4],
            "data_vencimento": cobranca[5],
            "valor": cobranca[6],
            "desconto": cobranca[7],
            "status": cobranca[8],
            "total_recebido": cobranca[9],
            "total_multa_juros": cobranca[10],
            "total_recebido_com_encargos": cobranca[9] + cobranca[10],
            "data_pagamento": cobranca[11],
            "residente_nome": cobranca[12],
            "responsavel_nome": cobranca[13],
            "residente_id": cobranca[14],
            "modalidade": cobranca[15],
            "convenio_nome": cobranca[16],
        }
        for cobranca in cobrancas
    ]


def buscar_cobranca_consolidada(cobranca_id, data_referencia=None):
    """Busca uma cobrança com recebimentos consolidados. Não altera o banco."""
    cobrancas = _consultar_cobrancas(cobranca_id=cobranca_id)

    if not cobrancas:
        return None

    return consolidar_cobranca(cobrancas[0], data_referencia)


def listar_cobrancas_consolidadas(internacao_id=None, data_referencia=None):
    """Lista cobranças consolidadas.

    ``internacao_id`` restringe a uma internação.
    """
    cobrancas = _consultar_cobrancas(internacao_id=internacao_id)

    return [
        consolidar_cobranca(cobranca, data_referencia)
        for cobranca in cobrancas
    ]


def cadastrar_conta_avulsa(descricao, data_vencimento, valor):
    """Registra uma conta a receber sem vínculo obrigatório com uma internação."""
    descricao = str(descricao or "").strip()
    if not descricao:
        return {"sucesso": False, "erro": "Informe a origem ou descrição da conta."}
    try:
        date.fromisoformat(str(data_vencimento))
        valor = int(valor)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Vencimento ou valor inválido."}
    if valor <= 0:
        return {"sucesso": False, "erro": "O valor deve ser maior que zero."}
    conexao = conectar()
    try:
        cursor = conexao.execute(
            """INSERT INTO cobrancas
               (internacao_id,numero_parcela,tipo,descricao,data_vencimento,valor,desconto,status)
               VALUES(NULL,0,'OUTROS',?,?,?,0,'ABERTA')""",
            (descricao, data_vencimento, valor),
        )
        conexao.commit()
        return {"sucesso": True, "id": cursor.lastrowid, "tipo": "OUTROS"}
    except sqlite3.Error as erro:
        conexao.rollback()
        return {"sucesso": False, "erro": f"Não foi possível registrar a conta: {erro}"}
    finally:
        conexao.close()


def listar_mensalidades(data_referencia=None):
    """Lista as mensalidades com a identificação do residente."""
    mensalidades = [
        cobranca for cobranca in listar_cobrancas_consolidadas(data_referencia=data_referencia)
        if cobranca["tipo"] == "MENSALIDADE"
    ]
    conexao = conectar()
    try:
        residentes = {
            linha[0]: {"residente_id": linha[1], "residente_nome": linha[2],
                       "modalidade": linha[3], "convenio_nome": linha[4]}
            for linha in conexao.execute(
                """SELECT i.id,r.id,r.nome,i.modalidade,c.nome FROM internacoes i
                   JOIN residentes r ON r.id=i.residente_id
                   LEFT JOIN convenios c ON c.id=i.convenio_id"""
            )
        }
    finally:
        conexao.close()
    return [{**mensalidade, **residentes.get(mensalidade["internacao_id"], {})} for mensalidade in mensalidades]


def listar_cobrancas_paginadas(data_referencia=None, tipo=None, busca=None, pagina=1, tamanho=50):
    """Retorna somente a página solicitada, preservando o formato consolidado."""
    try:
        pagina, tamanho = int(pagina), int(tamanho)
    except (TypeError, ValueError) as erro:
        raise ValueError("Paginação inválida.") from erro
    if pagina < 1 or not 10 <= tamanho <= 100:
        raise ValueError("Paginação inválida.")
    busca = (busca or "").strip()

    conexao = conectar()
    try:
        filtro_tipo = " WHERE c.tipo=?" if tipo else ""
        params_tipo = [tipo] if tipo else []
        total_registros = conexao.execute(
            f"SELECT COUNT(*) FROM cobrancas c{filtro_tipo}", params_tipo
        ).fetchone()[0]
        filtro_busca = (" AND" if filtro_tipo else " WHERE") + \
            " (res.nome LIKE ? OR c.descricao LIKE ?)" if busca else ""
        params_filtro = [*params_tipo]
        if busca:
            termo = f"%{busca}%"
            params_filtro.extend((termo, termo))
        total_filtrado = conexao.execute(
            f"""SELECT COUNT(*) FROM cobrancas c
                LEFT JOIN internacoes i ON i.id=c.internacao_id
                LEFT JOIN residentes res ON res.id=i.residente_id
                {filtro_tipo}{filtro_busca}""", params_filtro,
        ).fetchone()[0]
    finally:
        conexao.close()

    linhas = [consolidar_cobranca(item, data_referencia) for item in _consultar_cobrancas(
        tipo=tipo, busca=busca, limite=tamanho, deslocamento=(pagina - 1) * tamanho,
    )]
    return {
        "linhas": linhas, "pagina": pagina, "tamanho": tamanho,
        "total_registros": total_registros, "total_filtrado": total_filtrado,
    }


"""Motor de consulta de contas a receber.

Consolida cobranças (o que deveria ser recebido) com recebimentos (o que
entrou), sem alterar dados persistidos, vencimentos ou status financeiro.
"""

from datetime import date

from .banco import conectar
from .parcelas import calcular_status_parcela
from .regras_financeiras import (
    calcular_saldo_restante,
    calcular_valor_devido,
)


def _situacao_temporal(cobranca, data_referencia=None):
    """Calcula a situação temporal sem substituir o status financeiro salvo.

    ``PARCIAL`` e ``DESCONTADA`` não recebem mapeamento temporal porque suas
    regras financeiras não são equivalentes aos estados do motor de parcelas.
    """
    status_financeiro = cobranca["status"]

    if status_financeiro == "ABERTA":
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
        "numero_parcela": cobranca["numero_parcela"],
        "tipo": cobranca["tipo"],
        "data_vencimento": cobranca["data_vencimento"],
        "valor": valor,
        "desconto": desconto,
        "status": cobranca["status"],
        "valor_devido": valor_devido,
        "total_recebido": total_recebido,
        "saldo_restante": saldo_restante,
        "data_pagamento": cobranca["data_pagamento"],
        "situacao_temporal": _situacao_temporal(cobranca, data_referencia),
        "paga_em_atraso": _paga_em_atraso(
            cobranca["status"],
            cobranca["data_vencimento"],
            cobranca["data_pagamento"],
        ),
    }


def _consultar_cobrancas(cobranca_id=None, internacao_id=None):
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

    where = " WHERE " + " AND ".join(filtros) if filtros else ""

    cobrancas = cursor.execute(
        f"""
        SELECT
            c.id,
            c.internacao_id,
            c.numero_parcela,
            c.tipo,
            c.data_vencimento,
            c.valor,
            c.desconto,
            c.status,
            COALESCE(SUM(r.valor), 0) AS total_recebido,
            MAX(r.data_recebimento) AS data_pagamento
        FROM cobrancas c
        LEFT JOIN recebimentos r
            ON r.cobranca_id = c.id
        {where}
        GROUP BY c.id
        ORDER BY c.internacao_id, c.numero_parcela
        """,
        parametros,
    ).fetchall()

    conexao.close()

    return [
        {
            "id": cobranca[0],
            "internacao_id": cobranca[1],
            "numero_parcela": cobranca[2],
            "tipo": cobranca[3],
            "data_vencimento": cobranca[4],
            "valor": cobranca[5],
            "desconto": cobranca[6],
            "status": cobranca[7],
            "total_recebido": cobranca[8],
            "data_pagamento": cobranca[9],
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

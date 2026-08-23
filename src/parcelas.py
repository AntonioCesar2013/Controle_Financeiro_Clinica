"""Motor puro para vencimento e status de parcelas.

Este módulo não acessa banco de dados nem contém regras de valor de tratamento.
"""

from calendar import monthrange
from datetime import date, datetime


def _normalizar_data(valor, nome_campo):
    """Aceita ``date`` ou texto ISO estrito e retorna um objeto ``date``."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if not isinstance(valor, str):
        raise ValueError(f"{nome_campo} deve ser uma data no formato YYYY-MM-DD.")

    try:
        data_convertida = date.fromisoformat(valor)
    except ValueError as erro:
        raise ValueError(
            f"{nome_campo} deve ser uma data no formato YYYY-MM-DD."
        ) from erro

    if data_convertida.isoformat() != valor:
        raise ValueError(f"{nome_campo} deve ser uma data no formato YYYY-MM-DD.")
    return data_convertida


def _validar_numero_parcela(numero_parcela):
    if isinstance(numero_parcela, bool) or not isinstance(numero_parcela, int):
        raise ValueError("O número da parcela deve ser um inteiro maior que zero.")
    if numero_parcela <= 0:
        raise ValueError("O número da parcela deve ser maior que zero.")
    return numero_parcela


def calcular_data_vencimento(data_acolhimento, numero_parcela):
    """Calcula o vencimento da parcela, mantendo o dia do acolhimento.

    A parcela 1 vence um mês após o acolhimento. O dia do acolhimento é sempre
    o dia-base; quando ele não existe no mês calculado, usa-se o último dia
    desse mês.
    """
    acolhimento = _normalizar_data(data_acolhimento, "data de acolhimento")
    numero_parcela = _validar_numero_parcela(numero_parcela)

    mes_total = acolhimento.month - 1 + numero_parcela
    ano = acolhimento.year + mes_total // 12
    mes = mes_total % 12 + 1
    ultimo_dia_mes = monthrange(ano, mes)[1]
    return date(ano, mes, min(acolhimento.day, ultimo_dia_mes))


def calcular_status_parcela(data_vencimento, data_pagamento=None, data_referencia=None):
    """Determina o status como PAGA, PENDENTE ou ATRASADA."""
    vencimento = _normalizar_data(data_vencimento, "data de vencimento")

    if data_pagamento is not None:
        _normalizar_data(data_pagamento, "data de pagamento")
        return "PAGA"

    referencia = (
        _normalizar_data(data_referencia, "data de referência")
        if data_referencia is not None
        else date.today()
    )
    return "PENDENTE" if referencia <= vencimento else "ATRASADA"


def criar_parcela(
    data_acolhimento,
    numero_parcela,
    valor=None,
    data_pagamento=None,
    data_referencia=None,
):
    """Cria os dados de uma parcela sem calcular ou alterar o seu valor."""
    vencimento = calcular_data_vencimento(data_acolhimento, numero_parcela)
    pagamento = (
        _normalizar_data(data_pagamento, "data de pagamento")
        if data_pagamento is not None
        else None
    )
    return {
        "numero_parcela": numero_parcela,
        "valor": valor,
        "data_vencimento": vencimento.isoformat(),
        "data_pagamento": pagamento.isoformat() if pagamento else None,
        "status": calcular_status_parcela(vencimento, pagamento, data_referencia),
    }


def gerar_parcelas(
    data_acolhimento,
    numeros_parcelas,
    valores_por_parcela=None,
    pagamentos_por_parcela=None,
    data_referencia=None,
):
    """Gera parcelas para os números fornecidos pelo chamador.

    ``valores_por_parcela`` e ``pagamentos_por_parcela`` são mapeamentos
    opcionais por número de parcela. Nenhum valor ou quantidade é inferido.
    """
    valores_por_parcela = valores_por_parcela or {}
    pagamentos_por_parcela = pagamentos_por_parcela or {}
    return [
        criar_parcela(
            data_acolhimento=data_acolhimento,
            numero_parcela=numero,
            valor=valores_por_parcela.get(numero),
            data_pagamento=pagamentos_por_parcela.get(numero),
            data_referencia=data_referencia,
        )
        for numero in numeros_parcelas
    ]

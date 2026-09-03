"""Regras financeiras puras do sistema.

Este módulo não acessa banco de dados e não altera dados persistidos.

Responsabilidades atuais:
- calcular o valor devido após desconto;
- calcular o saldo restante da cobrança.

Juros, multa, mora e correção monetária ainda não fazem parte destas regras.
"""


def calcular_valor_devido(valor, desconto):
    """Calcula o valor efetivamente devido após o desconto.

    Args:
        valor: Valor original da cobrança.
        desconto: Valor do desconto aplicado.

    Returns:
        Valor devido após o desconto.
    """
    return valor - desconto


def calcular_saldo_restante(valor_devido, total_recebido):
    """Calcula quanto ainda falta receber, nunca retornando valor negativo.

    Args:
        valor_devido: Valor que deveria ser recebido após descontos.
        total_recebido: Soma dos recebimentos já registrados.

    Returns:
        Saldo restante da cobrança.
    """
    return max(valor_devido - total_recebido, 0)

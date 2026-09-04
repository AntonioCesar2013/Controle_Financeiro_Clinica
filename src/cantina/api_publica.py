"""Operações públicas da Cantina para consumidores externos."""

from src.cantina.vendas import consultar_carteira


def obter_saldo_residente(carteira_id):
    """Retorna os dados da carteira; o saldo pode ser negativo por regra."""
    return consultar_carteira(carteira_id)

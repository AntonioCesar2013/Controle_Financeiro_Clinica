"""Interface pública estável oferecida pelo módulo Financeiro.

As funções aceitam ``conexao`` para participar da transação iniciada pelo
chamador. Erros de regra são retornados no resultado ou levantados como
``ValueError`` pelas rotinas de ajuste, preservando a API existente.
"""

from src.financeiro.cobrancas import ajustar_convenio_ao_encerrar, gerar_cobrancas
from src.financeiro.parcelas import calcular_data_vencimento


def criar_contrato_internacao(internacao_id, conexao=None):
    """Gera as cobranças da internação e retorna o resultado do Financeiro."""
    return gerar_cobrancas(internacao_id, conexao=conexao)


def ajustar_contrato_encerramento(
    internacao_id, data_encerramento, conexao=None, autorizar_ajuste_desconto=False
):
    """Recalcula o contrato de convênio na transação fornecida."""
    return ajustar_convenio_ao_encerrar(
        internacao_id,
        data_encerramento,
        conexao=conexao,
        autorizar_ajuste_desconto=autorizar_ajuste_desconto,
    )


def data_final_contrato(data_acolhimento, periodo_tratamento):
    return calcular_data_vencimento(data_acolhimento, periodo_tratamento)

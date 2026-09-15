"""Índices medidos para os relacionamentos e filtros operacionais frequentes."""


INDICES = (
    "CREATE INDEX IF NOT EXISTS idx_recebimentos_cobranca_data ON recebimentos(cobranca_id, data_recebimento, id)",
    "CREATE INDEX IF NOT EXISTS idx_recebimentos_data_id ON recebimentos(data_recebimento, id)",
    "CREATE INDEX IF NOT EXISTS idx_pagamentos_conta_data ON pagamentos_saida(conta_pagar_id, data_pagamento, id)",
    "CREATE INDEX IF NOT EXISTS idx_pagamentos_data_id ON pagamentos_saida(data_pagamento, id)",
    "CREATE INDEX IF NOT EXISTS idx_contas_pagar_status_vencimento ON contas_pagar(status, data_vencimento, id)",
    "CREATE INDEX IF NOT EXISTS idx_cobrancas_status_vencimento ON cobrancas(status, data_vencimento, id)",
    "CREATE INDEX IF NOT EXISTS idx_mov_carteira_carteira_data ON movimentacoes_carteira(carteira_id, data_movimentacao, id)",
    "CREATE INDEX IF NOT EXISTS idx_mov_carteira_data_id ON movimentacoes_carteira(data_movimentacao, id)",
    "CREATE INDEX IF NOT EXISTS idx_mov_estoque_item_data ON movimentacoes_estoque(item_id, data_movimentacao, id)",
    "CREATE INDEX IF NOT EXISTS idx_internacoes_residente_datas ON internacoes(residente_id, data_acolhimento, encerrada_em, id)",
    "CREATE INDEX IF NOT EXISTS idx_item_valores_vigencia ON itens_cantina_valores(item_id, data_inicio_valor DESC, id DESC)",
    "CREATE INDEX IF NOT EXISTS idx_entradas_bancarias_data_id ON entradas_bancarias(data_entrada, id)",
    "CREATE INDEX IF NOT EXISTS idx_devolucoes_data_ativa ON devolucoes_recebimentos(data_devolucao, estornada, id)",
)


def aplicar(conexao):
    for comando in INDICES:
        conexao.execute(comando)

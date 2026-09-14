"""Bloqueia alterações de movimentos pertencentes a meses fechados."""


TABELAS_DATAS = (
    ("recebimentos", "data_recebimento"),
    ("pagamentos_saida", "data_pagamento"),
    ("movimentacoes_carteira", "data_movimentacao"),
    ("movimentacoes_estoque", "data_movimentacao"),
    ("entradas_bancarias", "data_entrada"),
    ("devolucoes_recebimentos", "data_devolucao"),
)


def aplicar(conn):
    existentes = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    for tabela, campo in TABELAS_DATAS:
        if tabela not in existentes:
            continue
        for evento, referencia, sufixo in (
            ("INSERT", "NEW", "insert"),
            ("UPDATE", "OLD", "update_old"),
            ("UPDATE", "NEW", "update_new"),
            ("DELETE", "OLD", "delete"),
        ):
            nome = f"bloquear_periodo_fechado_{tabela}_{sufixo}"
            conn.execute(f"""CREATE TRIGGER {nome} BEFORE {evento} ON {tabela}
                WHEN EXISTS(
                    SELECT 1 FROM fechamentos_mensais f
                    WHERE f.competencia=substr({referencia}.{campo},1,7)
                      AND f.reaberto_em IS NULL
                )
                BEGIN
                    SELECT RAISE(ABORT,
                        'O período financeiro está fechado. Reabra o mês com motivo antes de alterar este lançamento.');
                END""")

"""Estorno de erro de lançamento, preservando a devolução original."""


def aplicar(conn):
    colunas = {linha[1] for linha in conn.execute('PRAGMA table_info(devolucoes_recebimentos)')}
    if 'multa_juros' not in colunas:
        conn.execute("ALTER TABLE devolucoes_recebimentos ADD COLUMN multa_juros INTEGER NOT NULL DEFAULT 0 CHECK(typeof(multa_juros)='integer' AND multa_juros>=0)")
    conn.execute('ALTER TABLE devolucoes_recebimentos ADD COLUMN estornada INTEGER NOT NULL DEFAULT 0 CHECK(estornada IN (0,1))')
    conn.execute('ALTER TABLE devolucoes_recebimentos ADD COLUMN estornada_em TEXT')
    conn.execute('ALTER TABLE devolucoes_recebimentos ADD COLUMN motivo_estorno TEXT')
    conn.execute('DROP VIEW IF EXISTS recebimentos_liquidos')
    conn.execute('''CREATE VIEW recebimentos_liquidos AS
        SELECT r.id,r.cobranca_id,r.data_recebimento,
          r.valor-COALESCE((SELECT SUM(d.valor) FROM devolucoes_recebimentos d WHERE d.recebimento_id=r.id AND d.estornada=0),0) AS valor,
          r.desconto,
          r.multa_juros-COALESCE((SELECT SUM(d.multa_juros) FROM devolucoes_recebimentos d WHERE d.recebimento_id=r.id AND d.estornada=0),0) AS multa_juros,
          r.forma_recebimento,r.observacao FROM recebimentos r''')

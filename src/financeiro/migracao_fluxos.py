"""Estruturas de acerto e recorrência, sem reescrever lançamentos anteriores."""


def aplicar(conn):
    conn.execute('''CREATE TABLE devolucoes_recebimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recebimento_id INTEGER NOT NULL REFERENCES recebimentos(id),
        valor INTEGER NOT NULL CHECK(typeof(valor)='integer' AND valor>=0),
        multa_juros INTEGER NOT NULL DEFAULT 0 CHECK(typeof(multa_juros)='integer' AND multa_juros>=0),
        data_devolucao TEXT NOT NULL, forma_pagamento TEXT NOT NULL,
        motivo TEXT NOT NULL, documento TEXT NOT NULL,
        registrada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CHECK(valor+multa_juros>0))''')
    conn.execute('CREATE INDEX devolucoes_por_recebimento ON devolucoes_recebimentos(recebimento_id)')
    conn.execute('''CREATE VIEW recebimentos_liquidos AS
        SELECT r.id,r.cobranca_id,r.data_recebimento,
               r.valor-COALESCE((SELECT SUM(d.valor) FROM devolucoes_recebimentos d WHERE d.recebimento_id=r.id),0) AS valor,
               r.desconto,
               r.multa_juros-COALESCE((SELECT SUM(d.multa_juros) FROM devolucoes_recebimentos d WHERE d.recebimento_id=r.id),0) AS multa_juros,
               r.forma_recebimento,r.observacao
        FROM recebimentos r''')
    for evento in ('DELETE', 'UPDATE'):
        conn.execute(f'''CREATE TRIGGER preservar_recebimento_devolvido_{evento.lower()}
            BEFORE {evento} ON recebimentos
            WHEN EXISTS(SELECT 1 FROM devolucoes_recebimentos WHERE recebimento_id=OLD.id)
            BEGIN SELECT RAISE(ABORT,'Recebimento com devolução não pode ser alterado ou estornado.'); END''')
    conn.execute('''CREATE TABLE recorrencias_despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, despesa_id INTEGER NOT NULL REFERENCES despesas(id),
        valor INTEGER NOT NULL CHECK(typeof(valor)='integer' AND valor>0),
        data_inicio TEXT NOT NULL, data_fim TEXT NOT NULL,
        intervalo_meses INTEGER NOT NULL CHECK(intervalo_meses BETWEEN 1 AND 12),
        ativo INTEGER NOT NULL DEFAULT 1, criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('CREATE UNIQUE INDEX recorrencia_ativa_despesa ON recorrencias_despesas(despesa_id) WHERE ativo=1')
    conn.execute('ALTER TABLE contas_pagar ADD COLUMN recorrencia_id INTEGER REFERENCES recorrencias_despesas(id)')
    conn.execute('CREATE UNIQUE INDEX conta_recorrencia_vencimento ON contas_pagar(recorrencia_id,data_vencimento) WHERE recorrencia_id IS NOT NULL')
    conn.execute('''CREATE TABLE prorrogacoes_internacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, internacao_id INTEGER NOT NULL REFERENCES internacoes(id),
        periodo_anterior INTEGER NOT NULL, periodo_novo INTEGER NOT NULL,
        motivo TEXT NOT NULL, registrada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE acertos_encerramento (
        id INTEGER PRIMARY KEY AUTOINCREMENT, internacao_id INTEGER NOT NULL UNIQUE REFERENCES internacoes(id),
        data_encerramento TEXT NOT NULL, politica TEXT NOT NULL, motivo TEXT NOT NULL,
        dados TEXT NOT NULL, registrado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')

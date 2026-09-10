"""Estruturas de conciliação e evidências imutáveis de conferência."""


def aplicar(conn):
    comandos = [
        """CREATE TABLE conciliacoes_bancarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entrada_id INTEGER NOT NULL REFERENCES entradas_bancarias(id),
            destino TEXT NOT NULL CHECK(destino IN ('RECEBIMENTO','CARTEIRA','OUTRA_RECEITA')),
            motivo TEXT NOT NULL, vinculos_originais TEXT NOT NULL DEFAULT '[]',
            criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            desfeita_em TEXT, motivo_desfazer TEXT)""",
        """CREATE UNIQUE INDEX conciliacao_entrada_ativa ON conciliacoes_bancarias(entrada_id)
            WHERE desfeita_em IS NULL""",
        """CREATE TABLE conciliacoes_vinculos (
            conciliacao_id INTEGER NOT NULL REFERENCES conciliacoes_bancarias(id),
            recebimento_id INTEGER REFERENCES recebimentos(id),
            movimento_id INTEGER REFERENCES movimentacoes_carteira(id),
            CHECK ((recebimento_id IS NOT NULL) != (movimento_id IS NOT NULL)))""",
        "CREATE UNIQUE INDEX vinculo_recebimento ON conciliacoes_vinculos(recebimento_id) WHERE recebimento_id IS NOT NULL",
        "CREATE UNIQUE INDEX vinculo_credito ON conciliacoes_vinculos(movimento_id) WHERE movimento_id IS NOT NULL",
        """CREATE TABLE conferencias_saldos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            responsavel TEXT NOT NULL, observacao TEXT NOT NULL, status TEXT NOT NULL,
            dados TEXT NOT NULL)""",
        """CREATE TABLE fechamentos_mensais (
            id INTEGER PRIMARY KEY AUTOINCREMENT, competencia TEXT NOT NULL,
            revisao INTEGER NOT NULL, responsavel TEXT NOT NULL, observacao TEXT NOT NULL,
            dados TEXT NOT NULL, assinatura TEXT NOT NULL,
            fechado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reaberto_em TEXT, motivo_reabertura TEXT,
            UNIQUE(competencia,revisao))""",
        """CREATE UNIQUE INDEX fechamento_ativo ON fechamentos_mensais(competencia)
            WHERE reaberto_em IS NULL""",
    ]
    for sql in comandos:
        conn.execute(sql)
    # Um lançamento conciliado só pode ser corrigido após desfazer o vínculo.
    # A regra também protege importadores e chamadas diretas ao domínio.
    for tabela, coluna, campos in (
        ('recebimentos', 'recebimento_id', 'valor,data_recebimento,cobranca_id'),
        ('movimentacoes_carteira', 'movimento_id', 'valor_total,data_movimentacao,tipo,estornada,carteira_id'),
    ):
        for evento, sufixo in ((f'UPDATE OF {campos}', 'update'), ('DELETE', 'delete')):
            conn.execute(f"""CREATE TRIGGER proteger_conciliado_{tabela}_{sufixo}
                BEFORE {evento} ON {tabela}
                WHEN EXISTS(SELECT 1 FROM conciliacoes_vinculos WHERE {coluna}=OLD.id)
                BEGIN SELECT RAISE(ABORT, 'Desfaça a conciliação bancária antes de alterar este lançamento.'); END""")
    conn.execute("""CREATE TRIGGER proteger_entrada_conciliada BEFORE UPDATE ON entradas_bancarias
        WHEN EXISTS(SELECT 1 FROM conciliacoes_bancarias WHERE entrada_id=OLD.id AND desfeita_em IS NULL)
        BEGIN SELECT RAISE(ABORT, 'Desfaça a conciliação antes de alterar a entrada bancária.'); END""")

import sqlite3
from pathlib import Path


# Caminho do banco de dados
BASE_DIR = Path(__file__).resolve().parents[2]
CAMINHO_BANCO = BASE_DIR / "dados" / "clinica.db"


def conectar():
    CAMINHO_BANCO.parent.mkdir(exist_ok=True)
    conexao = sqlite3.connect(CAMINHO_BANCO, timeout=30)
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA busy_timeout = 30000")
    return conexao


def _preparar_schema_legado():
    from src.infraestrutura.migracao_centavos import backup_antes_migracao, migrar
    backup_antes_migracao(CAMINHO_BANCO)

    conexao = conectar()
    conexao.execute("PRAGMA foreign_keys = OFF")
    cursor = conexao.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS recibos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, recebimento_id INTEGER NOT NULL UNIQUE,
        dados TEXT NOT NULL, emitido_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS estornos_financeiros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tabela TEXT NOT NULL, lancamento_id INTEGER NOT NULL, origem_id INTEGER NOT NULL,
        dados TEXT NOT NULL, motivo TEXT NOT NULL,
        estornada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tabela,lancamento_id))""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS ajustes_cobrancas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cobranca_id INTEGER NOT NULL,
        valor_anterior INTEGER NOT NULL, valor_novo INTEGER NOT NULL,
        desconto_anterior INTEGER NOT NULL, desconto_novo INTEGER NOT NULL,
        motivo TEXT NOT NULL, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    # ============================================================
    # RESIDENTES
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS residentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            cidade_origem TEXT,
            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ============================================================
    # RESPONSÁVEIS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS responsaveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            telefone TEXT,
            email TEXT,
            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ============================================================
    # COLABORADORES
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS colaboradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome TEXT NOT NULL
                CHECK (LENGTH(TRIM(nome)) > 0),

            cpf TEXT NOT NULL UNIQUE
                CHECK (LENGTH(TRIM(cpf)) > 0),

            senha_hash TEXT NOT NULL
                CHECK (LENGTH(TRIM(senha_hash)) > 0),

            status TEXT NOT NULL DEFAULT 'ATIVO'
                CHECK (status IN ('ATIVO', 'INATIVO')),

            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id INTEGER,
            colaborador_nome TEXT,
            acao TEXT NOT NULL,
            entidade TEXT NOT NULL,
            entidade_id TEXT,
            detalhes TEXT,
            endereco_ip TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id)
        )
    """)

    # ============================================================
    # RELAÇÃO RESIDENTE x RESPONSÁVEL
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS residente_responsavel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            residente_id INTEGER NOT NULL,
            responsavel_id INTEGER NOT NULL,

            relacao TEXT,

            principal INTEGER NOT NULL DEFAULT 0,

            UNIQUE (residente_id, responsavel_id),

            FOREIGN KEY (residente_id)
                REFERENCES residentes (id),

            FOREIGN KEY (responsavel_id)
                REFERENCES responsaveis (id)
        )
    """)

    # ============================================================
    # CONVÊNIOS E INTERNAÇÕES
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS convenios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            valor_diaria INTEGER NOT NULL CHECK (valor_diaria >= 0),
            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS internacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            residente_id INTEGER NOT NULL,
            responsavel_id INTEGER NOT NULL,

            data_acolhimento TEXT NOT NULL,
            periodo_tratamento INTEGER NOT NULL,

            valor_contrato INTEGER NOT NULL,
            valor_acolhimento INTEGER NOT NULL,
            valor_mensalidade INTEGER NOT NULL,

            status TEXT NOT NULL DEFAULT 'ATIVA',
            encerrada_em TEXT,
            motivo_encerramento TEXT,
            modalidade TEXT NOT NULL DEFAULT 'PARTICULAR',
            convenio_id INTEGER,
            valor_diaria INTEGER NOT NULL DEFAULT 0,
            servicos_voluntario TEXT,

            FOREIGN KEY (residente_id)
                REFERENCES residentes (id),

            FOREIGN KEY (responsavel_id)
                REFERENCES responsaveis (id),

            FOREIGN KEY (convenio_id)
                REFERENCES convenios (id)
        )
    """)

    # ============================================================
    # COBRANÇAS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cobrancas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            internacao_id INTEGER NOT NULL,

            numero_parcela INTEGER NOT NULL,
            tipo TEXT NOT NULL,

            data_vencimento TEXT NOT NULL,

            valor INTEGER NOT NULL,

            desconto INTEGER NOT NULL DEFAULT 0,

            status TEXT NOT NULL DEFAULT 'ABERTA',

            UNIQUE (internacao_id, numero_parcela),

            FOREIGN KEY (internacao_id)
                REFERENCES internacoes (id)
        )
    """)

    # ============================================================
    # RECEBIMENTOS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recebimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            cobranca_id INTEGER NOT NULL,

            data_recebimento TEXT NOT NULL,

            valor INTEGER NOT NULL,

            forma_recebimento TEXT NOT NULL,

            observacao TEXT,

            FOREIGN KEY (cobranca_id)
                REFERENCES cobrancas (id)
        )
    """)
    colunas_internacoes = {linha[1] for linha in cursor.execute("PRAGMA table_info(internacoes)")}
    if "encerrada_em" not in colunas_internacoes:
        cursor.execute("ALTER TABLE internacoes ADD COLUMN encerrada_em TEXT")
    if "motivo_encerramento" not in colunas_internacoes:
        cursor.execute("ALTER TABLE internacoes ADD COLUMN motivo_encerramento TEXT")
    if "modalidade" not in colunas_internacoes:
        cursor.execute("ALTER TABLE internacoes ADD COLUMN modalidade TEXT NOT NULL DEFAULT 'PARTICULAR'")
    if "convenio_id" not in colunas_internacoes:
        cursor.execute("ALTER TABLE internacoes ADD COLUMN convenio_id INTEGER")
    if "valor_diaria" not in colunas_internacoes:
        cursor.execute("ALTER TABLE internacoes ADD COLUMN valor_diaria INTEGER NOT NULL DEFAULT 0")
    if "servicos_voluntario" not in colunas_internacoes:
        cursor.execute("ALTER TABLE internacoes ADD COLUMN servicos_voluntario TEXT")

    # Entradas bancárias que ainda não possuem vínculo comprovado com cobrança.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entradas_bancarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_entrada TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor INTEGER NOT NULL CHECK (valor > 0),
            forma_recebimento TEXT NOT NULL DEFAULT 'PIX',
            origem_documento TEXT NOT NULL,
            observacao TEXT,
            UNIQUE (data_entrada, descricao, valor, origem_documento)
        )
    """)

    # ============================================================
    # SETORES
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS setores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome TEXT NOT NULL UNIQUE,

            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ============================================================
    # DESPESAS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            setor_id INTEGER NOT NULL,
            descricao TEXT NOT NULL,

            natureza TEXT NOT NULL,

            recorrente INTEGER NOT NULL DEFAULT 0,

            ativo INTEGER NOT NULL DEFAULT 1,

            FOREIGN KEY (setor_id)
                REFERENCES setores (id)
        )
    """)

    # Migra bancos anteriores preservando as despesas e eliminando o tipo redundante.
    colunas_despesas = {linha[1] for linha in cursor.execute("PRAGMA table_info(despesas)")}
    if "tipo_despesa_id" in colunas_despesas:
        cursor.execute("""
            CREATE TABLE despesas_sem_tipo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setor_id INTEGER NOT NULL,
                descricao TEXT NOT NULL,
                natureza TEXT NOT NULL,
                recorrente INTEGER NOT NULL DEFAULT 0,
                ativo INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (setor_id) REFERENCES setores (id)
            )
        """)
        cursor.execute("""INSERT INTO despesas_sem_tipo(id,setor_id,descricao,natureza,recorrente,ativo)
                          SELECT id,setor_id,descricao,natureza,recorrente,ativo FROM despesas""")
        cursor.execute("DROP TABLE despesas")
        cursor.execute("ALTER TABLE despesas_sem_tipo RENAME TO despesas")
    cursor.execute("DROP TABLE IF EXISTS tipos_despesa")

    # ============================================================
    # CONTAS A PAGAR
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contas_pagar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            despesa_id INTEGER NOT NULL,

            data_vencimento TEXT NOT NULL,

            valor INTEGER NOT NULL,

            desconto INTEGER NOT NULL DEFAULT 0,

            status TEXT NOT NULL DEFAULT 'ABERTA',

            FOREIGN KEY (despesa_id)
                REFERENCES despesas (id)
        )
    """)

    # ============================================================
    # PAGAMENTOS DE SAÍDA
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos_saida (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            conta_pagar_id INTEGER NOT NULL,

            data_pagamento TEXT NOT NULL,

            valor INTEGER NOT NULL,

            forma_pagamento TEXT NOT NULL,

            observacao TEXT,

            FOREIGN KEY (conta_pagar_id)
                REFERENCES contas_pagar (id)
        )
    """)

    # ============================================================
    # CONFIGURAÇÕES FINANCEIRAS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes_financeiras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            aplicar_juros INTEGER NOT NULL DEFAULT 0,
            tipo_juros TEXT NOT NULL DEFAULT 'PERCENTUAL',
            valor_juros INTEGER NOT NULL DEFAULT 0,

            aplicar_multa INTEGER NOT NULL DEFAULT 0,
            tipo_multa TEXT NOT NULL DEFAULT 'PERCENTUAL',
            valor_multa INTEGER NOT NULL DEFAULT 0,

            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ============================================================
    # CONFIGURAÇÃO FINANCEIRA PADRÃO
    # ============================================================

    cursor.execute("""
        INSERT INTO configuracoes_financeiras (
            aplicar_juros,
            tipo_juros,
            valor_juros,
            aplicar_multa,
            tipo_multa,
            valor_multa,
            ativo
        )
        SELECT 0, 'PERCENTUAL', 0, 0, 'PERCENTUAL', 0, 1
        WHERE NOT EXISTS (
            SELECT 1
            FROM configuracoes_financeiras
        )
    """)

    # ============================================================
    # ITENS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome TEXT NOT NULL UNIQUE,

            codigo_barras TEXT,
            descricao TEXT,
            categoria TEXT,
            unidade_medida TEXT NOT NULL DEFAULT 'UN',
            estoque_atual INTEGER NOT NULL DEFAULT 0,
            estoque_minimo INTEGER NOT NULL DEFAULT 0,

            ativo INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Migração compatível com bancos criados antes do cadastro completo da Cantina.
    colunas_itens = {linha[1] for linha in cursor.execute("PRAGMA table_info(itens)")}
    novas_colunas = {
        "codigo_barras": "TEXT",
        "descricao": "TEXT",
        "categoria": "TEXT",
        "unidade_medida": "TEXT NOT NULL DEFAULT 'UN'",
        "estoque_atual": "INTEGER NOT NULL DEFAULT 0",
        "estoque_minimo": "INTEGER NOT NULL DEFAULT 0",
    }
    for nome_coluna, definicao in novas_colunas.items():
        if nome_coluna not in colunas_itens:
            cursor.execute(f"ALTER TABLE itens ADD COLUMN {nome_coluna} {definicao}")
    cursor.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_itens_codigo_barras
                      ON itens(codigo_barras) WHERE codigo_barras IS NOT NULL""")

    # ============================================================
    # HISTÓRICO DE VALORES DOS ITENS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_valores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            item_id INTEGER NOT NULL,

            valor INTEGER NOT NULL,

            data_inicio_valor TEXT NOT NULL,

            ativo INTEGER NOT NULL DEFAULT 1,

            FOREIGN KEY (item_id)
                REFERENCES itens (id)
        )
    """)

    # ============================================================
    # CARTEIRAS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS carteiras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            residente_id INTEGER NOT NULL UNIQUE,

            saldo INTEGER NOT NULL DEFAULT 0,

            ativo INTEGER NOT NULL DEFAULT 1,

            FOREIGN KEY (residente_id)
                REFERENCES residentes (id)
        )
    """)

    # ============================================================
    # VENDAS DA CANTINA (CUPOM E ITENS)
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas_cantina (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carteira_id INTEGER NOT NULL,
            data_movimentacao TEXT NOT NULL,
            valor_total INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'FINALIZADA'
                CHECK (status IN ('FINALIZADA', 'ESTORNADA')),
            criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            estornada_em TEXT,
            motivo_estorno TEXT,
            FOREIGN KEY (carteira_id) REFERENCES carteiras (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas_cantina_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            item_valor_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL CHECK (quantidade > 0),
            valor_unitario INTEGER NOT NULL,
            valor_total INTEGER NOT NULL,
            FOREIGN KEY (venda_id) REFERENCES vendas_cantina (id),
            FOREIGN KEY (item_id) REFERENCES itens (id),
            FOREIGN KEY (item_valor_id) REFERENCES itens_valores (id)
        )
    """)

    # ============================================================
    # MOVIMENTAÇÕES DAS CARTEIRAS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes_carteira (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            carteira_id INTEGER NOT NULL,

            tipo TEXT NOT NULL,

            item_id INTEGER,

            quantidade INTEGER NOT NULL DEFAULT 1,

            item_valor_id INTEGER,

            valor_total INTEGER NOT NULL,

            data_movimentacao TEXT NOT NULL,
            venda_id INTEGER,
            estornada INTEGER NOT NULL DEFAULT 0,
            estornada_em TEXT,
            motivo_estorno TEXT,

            FOREIGN KEY (carteira_id)
                REFERENCES carteiras (id),

            FOREIGN KEY (item_id)
                REFERENCES itens (id),

            FOREIGN KEY (item_valor_id)
                REFERENCES itens_valores (id),

            FOREIGN KEY (venda_id)
                REFERENCES vendas_cantina (id)
        )
    """)
    colunas_movimentacoes = {linha[1] for linha in cursor.execute("PRAGMA table_info(movimentacoes_carteira)")}
    for nome_coluna, definicao in {
        "venda_id": "INTEGER",
        "estornada": "INTEGER NOT NULL DEFAULT 0",
        "estornada_em": "TEXT",
        "motivo_estorno": "TEXT",
    }.items():
        if nome_coluna not in colunas_movimentacoes:
            cursor.execute(f"ALTER TABLE movimentacoes_carteira ADD COLUMN {nome_coluna} {definicao}")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            quantidade_anterior INTEGER NOT NULL,
            quantidade_movimentada INTEGER NOT NULL,
            quantidade_atual INTEGER NOT NULL,
            motivo TEXT NOT NULL,
            data_movimentacao TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'AJUSTE',
            venda_id INTEGER,
            custo_unitario INTEGER,
            fornecedor TEXT,
            documento TEXT,
            lote TEXT,
            data_validade TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES itens (id),
            FOREIGN KEY (venda_id) REFERENCES vendas_cantina (id)
        )
    """)
    colunas_estoque = {linha[1] for linha in cursor.execute("PRAGMA table_info(movimentacoes_estoque)")}
    for nome_coluna, definicao in {
        "tipo": "TEXT NOT NULL DEFAULT 'AJUSTE'",
        "venda_id": "INTEGER",
        "custo_unitario": "INTEGER",
        "fornecedor": "TEXT",
        "documento": "TEXT",
        "lote": "TEXT",
        "data_validade": "TEXT",
        "criado_em": "TEXT",
    }.items():
        if nome_coluna not in colunas_estoque:
            cursor.execute(f"ALTER TABLE movimentacoes_estoque ADD COLUMN {nome_coluna} {definicao}")

    try:
        migrar(conexao)
        conexao.commit()
    except Exception:
        conexao.rollback()
        conexao.close()
        raise
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.close()


def criar_tabelas():
    """Prepara o banco único e coordena as migrações dos módulos.

    O bootstrap legado continua idempotente para aceitar todas as versões antigas
    do banco. Novas evoluções devem ser declaradas pelo módulo responsável.
    """
    from src.nucleo.modulos import preparar_modulos

    _preparar_schema_legado()
    conexao = conectar()
    try:
        with conexao:
            conexao.execute("BEGIN IMMEDIATE")
            preparar_modulos(conexao)
    finally:
        conexao.close()


if __name__ == "__main__":
    criar_tabelas()
    print("Banco de dados criado com sucesso.")

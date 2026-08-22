import sqlite3
from pathlib import Path


# Caminho do banco de dados
BASE_DIR = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = BASE_DIR / "dados" / "clinica.db"


def conectar():
    CAMINHO_BANCO.parent.mkdir(exist_ok=True)
    return sqlite3.connect(CAMINHO_BANCO)


def criar_tabelas():

    conexao = conectar()
    cursor = conexao.cursor()

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
    # INTERNAÇÕES
    # ============================================================

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

            FOREIGN KEY (residente_id)
                REFERENCES residentes (id),

            FOREIGN KEY (responsavel_id)
                REFERENCES responsaveis (id)
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
    # TIPOS DE DESPESA
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tipos_despesa (
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
            tipo_despesa_id INTEGER NOT NULL,

            descricao TEXT NOT NULL,

            natureza TEXT NOT NULL,

            recorrente INTEGER NOT NULL DEFAULT 0,

            ativo INTEGER NOT NULL DEFAULT 1,

            FOREIGN KEY (setor_id)
                REFERENCES setores (id),

            FOREIGN KEY (tipo_despesa_id)
                REFERENCES tipos_despesa (id)
        )
    """)

    # ============================================================
    # CONTAS A PAGAR
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contas_pagar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            despesa_id INTEGER NOT NULL,

            data_vencimento TEXT NOT NULL,

            valor INTEGER NOT NULL,

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

    conexao.commit()
    conexao.close()


if __name__ == "__main__":
    criar_tabelas()
    print("Banco de dados criado com sucesso.")
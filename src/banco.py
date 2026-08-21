import sqlite3
from pathlib import Path


# Caminho do banco de dados
BASE_DIR = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = BASE_DIR / "dados" / "clinica.db"


def conectar():
    """Cria e retorna uma conexão com o banco de dados."""
    CAMINHO_BANCO.parent.mkdir(exist_ok=True)
    return sqlite3.connect(CAMINHO_BANCO)


def criar_tabelas():
    """Cria as tabelas iniciais do sistema."""

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS residentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            cidade_origem TEXT,
            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS internacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            residente_id INTEGER NOT NULL,
            responsavel_id INTEGER NOT NULL,
            data_internacao TEXT NOT NULL,
            periodo_meses INTEGER NOT NULL,
            data_prevista_alta TEXT,
            data_alta_real TEXT,
            valor_tratamento INTEGER NOT NULL,
            valor_acolhimento INTEGER NOT NULL,
            valor_parcela INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'ATIVA',

            FOREIGN KEY (residente_id)
                REFERENCES residentes (id),

            FOREIGN KEY (responsavel_id)
                REFERENCES responsaveis (id)
        )
    """)

    conexao.commit()
    conexao.close()


if __name__ == "__main__":
    criar_tabelas()
    print("Banco de dados criado com sucesso.")
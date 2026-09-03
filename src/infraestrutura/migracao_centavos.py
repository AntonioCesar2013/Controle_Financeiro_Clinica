"""Migração atômica dos valores antigos em reais; preserva IDs e relacionamentos."""
import re
import sqlite3
from datetime import datetime
from src.financeiro.moeda import reais_para_centavos

CAMPOS = {
    "itens_valores": {"valor"}, "carteiras": {"saldo"},
    "vendas_cantina": {"valor_total"},
    "vendas_cantina_itens": {"valor_unitario", "valor_total"},
    "movimentacoes_carteira": {"valor_total"},
    "movimentacoes_estoque": {"custo_unitario"},
}


def tabelas_antigas(conn):
    return {tabela: campos for tabela, campos in CAMPOS.items()
            if any(nome in campos and tipo.upper() == "REAL"
                   for _, nome, tipo, *_ in conn.execute(f'PRAGMA table_info("{tabela}")'))}


def backup_antes_migracao(caminho):
    if not caminho.exists():
        return
    conn = sqlite3.connect(caminho)
    try:
        if not tabelas_antigas(conn):
            return
        pasta = caminho.parent / "backups"
        pasta.mkdir(exist_ok=True)
        destino = pasta / f"clinica_{datetime.now():%Y%m%d_%H%M%S_%f}_antes_centavos.db"
        copia = sqlite3.connect(destino)
        try:
            conn.backup(copia)
            if copia.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Falha ao validar backup antes da migração monetária.")
        finally:
            copia.close()
    finally:
        conn.close()


def migrar(conn):
    # O chamador já mantém foreign_keys OFF durante a migração de estrutura.
    conn.execute("SAVEPOINT migracao_centavos")
    try:
        for tabela, campos in tabelas_antigas(conn).items():
            esquema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tabela,)).fetchone()[0]
            auxiliares = conn.execute("SELECT sql FROM sqlite_master WHERE tbl_name=? AND type IN ('index','trigger') AND sql IS NOT NULL", (tabela,)).fetchall()
            sequencia = conn.execute("SELECT seq FROM sqlite_sequence WHERE name=?", (tabela,)).fetchone()
            temporaria = tabela + "_centavos_nova"
            novo = re.sub(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?["`\[]?' + tabela + r'["`\]]?', 'CREATE TABLE "' + temporaria + '"', esquema, count=1, flags=re.I)
            for campo in campos:
                novo = re.sub(r'\b' + campo + r'\s+REAL\b', campo + " INTEGER", novo, flags=re.I)
            conn.execute(novo)
            cursor = conn.execute(f'SELECT * FROM "{tabela}"')
            nomes = [coluna[0] for coluna in cursor.description]
            registros = cursor.fetchall()
            for linha in registros:
                valores = [reais_para_centavos(valor) if nome in campos and valor is not None else valor
                           for nome, valor in zip(nomes, linha)]
                conn.execute(f'INSERT INTO "{temporaria}" VALUES ({",".join("?" for _ in valores)})', valores)
            conn.execute(f'DROP TABLE "{tabela}"')
            conn.execute(f'ALTER TABLE "{temporaria}" RENAME TO "{tabela}"')
            if sequencia:
                atualizado = conn.execute("UPDATE sqlite_sequence SET seq=MAX(seq,?) WHERE name=?", (sequencia[0], tabela))
                if not atualizado.rowcount:
                    conn.execute("INSERT INTO sqlite_sequence(name,seq) VALUES(?,?)", (tabela, sequencia[0]))
            for sql, in auxiliares:
                conn.execute(sql)
        conn.execute("CREATE TABLE IF NOT EXISTS migracoes (versao TEXT PRIMARY KEY, aplicada_em TEXT DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("INSERT OR IGNORE INTO migracoes(versao) VALUES('cantina_centavos_v1')")
        conn.execute("RELEASE migracao_centavos")
    except Exception:
        conn.execute("ROLLBACK TO migracao_centavos")
        conn.execute("RELEASE migracao_centavos")
        raise

"""Importa as entradas bancárias reais do relatório Cora de agosto de 2026."""

from pathlib import Path
import sqlite3

from src.banco import CAMINHO_BANCO, criar_tabelas
from src.popular_despesas_reais import _backup


ORIGEM = "Relatorio_Movimentacao_Bancaria_Cora_Modelo_Sicredi.pdf"
ENTRADAS = (
    ("2026-08-01", "Pix recebido - Douglas Rafael Pinheiro", 6500),
    ("2026-08-03", "Pix recebido - Construtora Inovar Ltda", 11500),
    ("2026-08-04", "Pix recebido - ADILSON TRANSPO...", 60000),
    ("2026-08-04", "Pix recebido - LUCIMAR MARTINS", 12000),
    ("2026-08-05", "Pix recebido - EDITE ANA MEZZALI...", 9000),
    ("2026-08-05", "Pix recebido - LEUZINA COLOGNE...", 100000),
    ("2026-08-05", "Pix recebido - GRAO DE CAFE", 5000),
    ("2026-08-05", "Pix recebido - EDITE ANA MEZZALI...", 250000),
    ("2026-08-05", "Pix recebido - Sirley Pereira Souza ...", 5000),
    ("2026-08-05", "Pix recebido - MARCELO MUNIZ B...", 3000),
    ("2026-08-05", "Pix recebido - Carla Sabrina Steimb...", 1500),
    ("2026-08-05", "Pix recebido - Carla Sabrina Steimb...", 9000),
    ("2026-08-05", "Pix recebido - ADILSON TRANSPO...", 10000),
    ("2026-08-06", "Pix recebido - Clair Gamst Indrusczak", 10000),
    ("2026-08-06", "Pix recebido - Thiago Fernando Hof...", 10000),
    ("2026-08-06", "Pix recebido - DEOCELIA JOSEFIN...", 14000),
    ("2026-08-07", "Pix recebido - MAYKON DOUGLAS...", 100000),
    ("2026-08-07", "Pix recebido - MARCIO DE SOUZA", 200000),
    ("2026-08-07", "Pix recebido - Construtora Inovar Ltda", 9000),
    ("2026-08-08", "Pix recebido - MARCIO FRANCISC...", 20000),
    ("2026-08-09", "Pix recebido - LETICIA APARECIDA...", 6500),
    ("2026-08-09", "Pix recebido - ROSEMARI B MELLO", 9000),
    ("2026-08-10", "Pix recebido - EDILSON SOUZA M...", 230000),
    ("2026-08-10", "Pix recebido - Marcos Alexandre M...", 230000),
    ("2026-08-10", "Pix recebido - MARCIO DE SOUZA", 6500),
    ("2026-08-10", "Pix recebido - EDITE ANA MEZZALI...", 3350),
    ("2026-08-10", "Pix recebido - Elizandra Brenda Ferr...", 6500),
    ("2026-08-10", "Pix recebido - EDGAR RAMON SIL...", 6000),
    ("2026-08-10", "Pix recebido - João Paulo Cogo", 9000),
    ("2026-08-10", "Pix recebido - IVONE MARIA JUN...", 100000),
    ("2026-08-11", "Pix recebido - Carla Sabrina Steimb...", 1000),
    ("2026-08-11", "Pix recebido - Marcos Alexandre M...", 160000),
    ("2026-08-11", "Pix recebido - EDITE ANA MEZZALI...", 5000),
    ("2026-08-11", "Pix recebido - DAIANA EGER VIAN", 100000),
    ("2026-08-11", "Pix recebido - Clair Gamst Indrusczak", 20000),
    ("2026-08-11", "Pix recebido - Clinica De Recuperac...", 700000),
    ("2026-08-11", "Pix recebido - Rafaela Figura", 90000),
    ("2026-08-12", "Pix recebido - IOLANDA A L PINHE...", 10000),
    ("2026-08-12", "Pix recebido - Clinica De Recuperac...", 1000000),
    ("2026-08-12", "Pix recebido - Marcos Alexandre M...", 14000),
    ("2026-08-13", "Pix recebido - MIRELA FRANCINE ...", 100000),
    ("2026-08-13", "Pix recebido - DEOCELIA JOSEFIN...", 100000),
    ("2026-08-13", "Pix recebido - Daiane Rodrigues Ra...", 1800),
    ("2026-08-13", "Pix recebido - Clinica De Recuperac...", 240000),
    ("2026-08-13", "Pix recebido - IRICI STEIN", 180000),
    ("2026-08-14", "Pix recebido - DEOCELIA JOSEFIN...", 100000),
    ("2026-08-14", "Pix recebido - LETICIA APARECIDA...", 2000),
    ("2026-08-14", "Pix recebido - IRICI STEIN", 250000),
    ("2026-08-14", "Pix recebido - Antonio Martinho Za...", 6500),
    ("2026-08-14", "Pix recebido - EDILSON SOUZA M...", 5000),
    ("2026-08-15", "Pix recebido - JONATAS SOARES ...", 10000),
    ("2026-08-17", "Pix recebido - UENO", 15000),
    ("2026-08-17", "Pix recebido - João Paulo Cogo", 100000),
    ("2026-08-17", "Pix recebido - LETICIA APARECIDA...", 6500),
    ("2026-08-17", "Pix recebido - Antonio Martinho Za...", 250000),
    ("2026-08-17", "Pix recebido - IRICI STEIN", 8000),
    ("2026-08-18", "Pix recebido - MARIA CRISTINA PE...", 3000),
    ("2026-08-18", "Pix recebido - Carla Sabrina Steimb...", 1000),
    ("2026-08-18", "Pix recebido - ROSANA MIRIAN VI...", 10000),
    ("2026-08-18", "Pix recebido - Heloisa Gabriely Ham...", 180000),
    ("2026-08-19", "Pix recebido - Lenita Rodrigues", 2000),
    ("2026-08-19", "Pix recebido - Rosilene Lugli Bianchi...", 5000),
    ("2026-08-19", "Pix recebido - Heloisa Gabriely Ham...", 6000),
    ("2026-08-19", "Pix recebido - Marcos Alexandre M...", 150000),
)


def _garantir_tabela(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS entradas_bancarias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_entrada TEXT NOT NULL,
        descricao TEXT NOT NULL,
        valor INTEGER NOT NULL CHECK (valor > 0),
        forma_recebimento TEXT NOT NULL DEFAULT 'PIX',
        origem_documento TEXT NOT NULL,
        observacao TEXT,
        UNIQUE (data_entrada, descricao, valor, origem_documento)
    )""")


def popular(caminho_banco: Path = CAMINHO_BANCO, fazer_backup: bool = True):
    caminho_banco = Path(caminho_banco)
    if caminho_banco == CAMINHO_BANCO:
        criar_tabelas()
    backup = _backup(caminho_banco, "entradas_reais") if fazer_backup else None
    conn = sqlite3.connect(caminho_banco)
    try:
        _garantir_tabela(conn)
        conn.execute("BEGIN")
        conn.execute("DELETE FROM entradas_bancarias WHERE origem_documento = ?", (ORIGEM,))
        conn.executemany(
            """INSERT INTO entradas_bancarias
               (data_entrada, descricao, valor, forma_recebimento, origem_documento, observacao)
               VALUES (?, ?, ?, 'PIX', ?, ?)""",
            ((data, descricao, valor, ORIGEM,
              "Descrição preservada conforme exibida no relatório; reticências indicam texto truncado na fonte.")
             for data, descricao, valor in ENTRADAS),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"backup": backup, "quantidade": len(ENTRADAS), "total": sum(x[2] for x in ENTRADAS)}


if __name__ == "__main__":
    resultado = popular()
    print(f"{resultado['quantidade']} entradas registradas; total R$ {resultado['total'] / 100:,.2f}.")
    print(f"Backup: {resultado['backup']}")

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.banco import CAMINHO_BANCO
from src.popular_entradas_reais import ENTRADAS, popular


class PopularEntradasReaisTest(unittest.TestCase):
    def test_importacao_idempotente(self):
        with tempfile.TemporaryDirectory() as pasta:
            banco = Path(pasta) / "teste.db"
            origem = sqlite3.connect(CAMINHO_BANCO)
            destino = sqlite3.connect(banco)
            origem.backup(destino)
            origem.close(); destino.close()
            popular(banco, fazer_backup=False)
            popular(banco, fazer_backup=False)
            conn = sqlite3.connect(banco)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM entradas_bancarias").fetchone()[0], len(ENTRADAS))
            self.assertEqual(conn.execute("SELECT SUM(valor) FROM entradas_bancarias").fetchone()[0], 5284150)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM entradas_bancarias WHERE forma_recebimento='PIX'").fetchone()[0], len(ENTRADAS))
            conn.close()


if __name__ == "__main__":
    unittest.main()

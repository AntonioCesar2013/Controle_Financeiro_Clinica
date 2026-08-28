import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.banco import CAMINHO_BANCO
from src.popular_despesas_reais import COMPRAS_REAIS, popular


class PopularDespesasReaisTest(unittest.TestCase):
    def test_substitui_demonstracao_e_preserva_colaborador(self):
        with tempfile.TemporaryDirectory() as pasta:
            banco = Path(pasta) / "teste.db"
            origem = sqlite3.connect(CAMINHO_BANCO)
            destino = sqlite3.connect(banco)
            origem.backup(destino)
            origem.close()
            destino.close()

            resultado = popular(banco, fazer_backup=False)
            conn = sqlite3.connect(banco)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM residentes").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM colaboradores").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM despesas").fetchone()[0], len(COMPRAS_REAIS))
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM contas_pagar WHERE status='PAGA'").fetchone()[0], len(COMPRAS_REAIS))
            self.assertEqual(conn.execute("SELECT SUM(valor) FROM pagamentos_saida").fetchone()[0], resultado["total"])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM pagamentos_saida WHERE forma_pagamento='PIX'").fetchone()[0], 4)
            conn.close()


if __name__ == "__main__":
    unittest.main()

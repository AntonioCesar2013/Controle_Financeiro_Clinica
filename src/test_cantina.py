import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import cantina, itens
from src.banco import CAMINHO_BANCO


class CantinaTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.banco = Path(self.temp.name) / "cantina.db"
        origem = sqlite3.connect(CAMINHO_BANCO)
        destino = sqlite3.connect(self.banco)
        origem.backup(destino)
        origem.close(); destino.close()
        conn = sqlite3.connect(self.banco)
        conn.execute("INSERT INTO residentes (nome,cpf) VALUES ('Residente Teste','99999999999')")
        self.residente_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO itens (nome,estoque_atual,estoque_minimo) VALUES ('Refrigerante',10,2)")
        self.item_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO itens_valores (item_id,valor,data_inicio_valor) VALUES (?,5.50,'2026-01-01')", (self.item_id,))
        conn.commit(); conn.close()
        self.patcher = patch("src.cantina.conectar", side_effect=lambda: sqlite3.connect(self.banco))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_venda_desconta_saldo_e_preserva_preco(self):
        carteira = cantina.criar_carteira(self.residente_id, 20)
        venda = cantina.registrar_venda(carteira["id"], self.item_id, 2, "2026-08-28")
        self.assertTrue(venda["sucesso"])
        self.assertEqual(venda["valor_total"], 11)
        self.assertEqual(venda["saldo"], 9)
        conn = sqlite3.connect(self.banco)
        movimento = conn.execute("SELECT tipo,quantidade,valor_total FROM movimentacoes_carteira WHERE id=?", (venda["id"],)).fetchone()
        conn.close()
        self.assertEqual(movimento, ("COMPRA_CANTINA", 2, 11))

    def test_recusa_venda_sem_saldo(self):
        carteira = cantina.criar_carteira(self.residente_id, 5)
        venda = cantina.registrar_venda(carteira["id"], self.item_id, 2, "2026-08-28")
        self.assertFalse(venda["sucesso"])
        self.assertIn("Saldo insuficiente", venda["erro"])

    def test_consulta_saldo_e_historico_de_compras(self):
        carteira = cantina.criar_carteira(self.residente_id, 20)
        cantina.registrar_venda(carteira["id"], self.item_id, 2, "2026-08-28")
        detalhe = cantina.consultar_carteira(carteira["id"])
        self.assertTrue(detalhe["sucesso"])
        self.assertEqual(detalhe["carteira"]["saldo"], 9)
        self.assertEqual(len(detalhe["compras"]), 1)
        self.assertEqual(detalhe["compras"][0]["valor_unitario"], 5.5)
        self.assertEqual(detalhe["compras"][0]["valor_total"], 11)

    def test_cadastro_completo_do_produto(self):
        with patch("src.itens.CAMINHO_BANCO", self.banco):
            produto = itens.cadastrar_produto(
                "Água mineral", 3.5, 24, 6, "7891234567890",
                "Garrafa 500 ml", "Bebidas", "UN", 1, "2026-08-28",
            )
            self.assertTrue(produto["sucesso"])
            catalogo = itens.listar_itens(apenas_ativos=False)
            cadastrado = next(x for x in catalogo if x["id"] == produto["id"])
            self.assertEqual(cadastrado["estoque_atual"], 24)
            self.assertEqual(cadastrado["estoque_minimo"], 6)
            self.assertEqual(cadastrado["valor_atual"], 3.5)

    def test_venda_baixa_estoque(self):
        carteira = cantina.criar_carteira(self.residente_id, 20)
        cantina.registrar_venda(carteira["id"], self.item_id, 2, "2026-08-28")
        conn = sqlite3.connect(self.banco)
        estoque = conn.execute("SELECT estoque_atual FROM itens WHERE id=?", (self.item_id,)).fetchone()[0]
        conn.close()
        self.assertEqual(estoque, 8)


if __name__ == "__main__":
    unittest.main()

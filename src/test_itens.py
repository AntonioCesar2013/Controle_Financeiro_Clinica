"""Testes do cadastro e histórico de valores dos itens."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src import banco, itens


class TestItens(unittest.TestCase):
    """Testa os itens usando um banco temporário."""

    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        self.caminho_original_banco = banco.CAMINHO_BANCO
        self.caminho_original_itens = itens.CAMINHO_BANCO
        self.caminho_banco = Path(self.diretorio_temporario.name) / "clinica.db"
        banco.CAMINHO_BANCO = self.caminho_banco
        itens.CAMINHO_BANCO = self.caminho_banco
        banco.criar_tabelas()

    def tearDown(self):
        banco.CAMINHO_BANCO = self.caminho_original_banco
        itens.CAMINHO_BANCO = self.caminho_original_itens
        self.diretorio_temporario.cleanup()

    def test_cria_tabelas_com_nomenclatura_padronizada(self):
        conexao = sqlite3.connect(self.caminho_banco)
        try:
            tabelas = {
                linha[0]
                for linha in conexao.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            chave_estrangeira = conexao.execute(
                "PRAGMA foreign_key_list(movimentacoes_carteira)"
            ).fetchall()
        finally:
            conexao.close()

        self.assertIn("itens", tabelas)
        self.assertIn("itens_valores", tabelas)
        self.assertNotIn("item", tabelas)
        self.assertNotIn("item_valor", tabelas)
        self.assertIn(("itens_valores", "item_valor_id"), {
            (linha[2], linha[3]) for linha in chave_estrangeira
        })

    def test_cadastrar_e_buscar_item(self):
        resultado = itens.cadastrar_item("Desodorante")

        self.assertTrue(resultado["sucesso"])
        encontrado = itens.buscar_item(resultado["id"])
        self.assertTrue(encontrado["sucesso"])
        self.assertEqual(encontrado["nome"], "Desodorante")
        self.assertEqual(encontrado["ativo"], 1)

    def test_nao_permite_item_com_nome_vazio_ou_duplicado(self):
        self.assertFalse(itens.cadastrar_item("  ")["sucesso"])
        self.assertTrue(itens.cadastrar_item("Shampoo")["sucesso"])
        self.assertFalse(itens.cadastrar_item("Shampoo")["sucesso"])

    def test_lista_e_altera_status_do_item(self):
        primeiro = itens.cadastrar_item("Pasta de dente")
        itens.cadastrar_item("Shampoo")

        self.assertEqual(
            [item["nome"] for item in itens.listar_itens()],
            ["Pasta de dente", "Shampoo"],
        )
        self.assertTrue(itens.alterar_status_item(primeiro["id"], 0)["sucesso"])
        self.assertEqual(
            [item["nome"] for item in itens.listar_itens()],
            ["Shampoo"],
        )

    def test_cadastra_e_consulta_historico_de_valores(self):
        item = itens.cadastrar_item("Sabonete")
        primeiro = itens.cadastrar_valor_item(item["id"], 5.0, "2026-08-01")
        itens.cadastrar_valor_item(item["id"], 7.0, "2026-09-01")

        valor = itens.buscar_valor_item(item["id"], "2026-08-15")
        historico = itens.listar_valores_item(item["id"])

        self.assertTrue(primeiro["sucesso"])
        self.assertEqual(valor["valor"], 5.0)
        self.assertEqual([valor["valor"] for valor in historico], [7.0, 5.0])

    def test_altera_status_do_valor(self):
        item = itens.cadastrar_item("Creme")
        valor = itens.cadastrar_valor_item(item["id"], 10.0, "2026-08-01")

        self.assertTrue(itens.alterar_status_valor(valor["id"], 0)["sucesso"])
        self.assertFalse(itens.buscar_valor_item(item["id"])["sucesso"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

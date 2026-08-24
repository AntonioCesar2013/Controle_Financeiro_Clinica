"""Testes do cadastro e histórico de valores dos itens."""

import tempfile
import unittest
from pathlib import Path

from src import banco
from src.itens import (
    cadastrar_item,
    buscar_item,
    listar_itens,
    alterar_valor_item,
    listar_historico_valores,
    desativar_item,
)


class TestItens(unittest.TestCase):
    """Testa o cadastro de itens usando banco temporário."""

    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()

        self.caminho_original = banco.CAMINHO_BANCO
        banco.CAMINHO_BANCO = (
            Path(self.diretorio_temporario.name) / "clinica.db"
        )

        banco.criar_tabelas()

    def tearDown(self):
        banco.CAMINHO_BANCO = self.caminho_original
        self.diretorio_temporario.cleanup()

    # ============================================================
    # CADASTRO
    # ============================================================

    def test_cadastrar_item(self):
        resultado = cadastrar_item("Desodorante", 1500)

        self.assertTrue(resultado["sucesso"])
        self.assertIsNotNone(resultado["id"])
        self.assertEqual(resultado["nome"], "Desodorante")
        self.assertEqual(resultado["valor"], 1500)
        self.assertEqual(resultado["ativo"], 1)

    def test_cadastrar_item_com_valor_decimal(self):
        resultado = cadastrar_item("Shampoo", 12.50)

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["valor"], 12.50)

    def test_nao_permite_item_com_nome_vazio(self):
        resultado = cadastrar_item("", 1000)

        self.assertFalse(resultado["sucesso"])

    def test_nao_permite_item_com_valor_negativo(self):
        resultado = cadastrar_item("Chocolate", -100)

        self.assertFalse(resultado["sucesso"])

    def test_nao_permite_item_com_valor_zero(self):
        resultado = cadastrar_item("Item gratuito", 0)

        self.assertFalse(resultado["sucesso"])

    def test_nao_permite_item_duplicado(self):
        primeiro = cadastrar_item("Pasta de dente", 1000)
        self.assertTrue(primeiro["sucesso"])

        segundo = cadastrar_item("Pasta de dente", 1200)

        self.assertFalse(segundo["sucesso"])

    # ============================================================
    # CONSULTA
    # ============================================================

    def test_buscar_item(self):
        resultado = cadastrar_item("Shampoo", 2000)

        item = buscar_item(resultado["id"])

        self.assertIsNotNone(item)
        self.assertEqual(item["nome"], "Shampoo")
        self.assertEqual(item["valor"], 2000)
        self.assertEqual(item["ativo"], 1)

    def test_buscar_item_inexistente(self):
        item = buscar_item(9999)

        self.assertIsNone(item)

    def test_listar_itens(self):
        cadastrar_item("Desodorante", 1500)
        cadastrar_item("Pasta de dente", 1000)
        cadastrar_item("Shampoo", 2000)

        itens = listar_itens()

        self.assertEqual(len(itens), 3)
        self.assertEqual(itens[0]["nome"], "Desodorante")
        self.assertEqual(itens[1]["nome"], "Pasta de dente")
        self.assertEqual(itens[2]["nome"], "Shampoo")

    # ============================================================
    # ALTERAÇÃO DE VALOR
    # ============================================================

    def test_alterar_valor_item(self):
        resultado = cadastrar_item("Desodorante", 1500)

        alteracao = alterar_valor_item(
            resultado["id"],
            1800,
            "2026-08-24",
        )

        self.assertTrue(alteracao["sucesso"])
        self.assertEqual(alteracao["valor"], 1800)

        item = buscar_item(resultado["id"])

        self.assertEqual(item["valor"], 1800)

    def test_alteracao_de_valor_cria_historico(self):
        resultado = cadastrar_item("Shampoo", 2000)

        alterar_valor_item(
            resultado["id"],
            2500,
            "2026-08-24",
        )

        historico = listar_historico_valores(resultado["id"])

        self.assertEqual(len(historico), 2)

        self.assertEqual(historico[0]["valor"], 2000)
        self.assertEqual(historico[1]["valor"], 2500)

    def test_alterar_valor_nao_permite_valor_zero(self):
        resultado = cadastrar_item("Chocolate", 500)

        alteracao = alterar_valor_item(
            resultado["id"],
            0,
            "2026-08-24",
        )

        self.assertFalse(alteracao["sucesso"])

    def test_alterar_valor_nao_permite_valor_negativo(self):
        resultado = cadastrar_item("Chocolate", 500)

        alteracao = alterar_valor_item(
            resultado["id"],
            -100,
            "2026-08-24",
        )

        self.assertFalse(alteracao["sucesso"])

    # ============================================================
    # HISTÓRICO
    # ============================================================

    def test_historico_mantem_valores_anteriores(self):
        resultado = cadastrar_item("Sabonete", 500)

        alterar_valor_item(
            resultado["id"],
            700,
            "2026-08-24",
        )

        alterar_valor_item(
            resultado["id"],
            900,
            "2026-09-01",
        )

        historico = listar_historico_valores(resultado["id"])

        self.assertEqual(len(historico), 3)

        self.assertEqual(historico[0]["valor"], 500)
        self.assertEqual(historico[1]["valor"], 700)
        self.assertEqual(historico[2]["valor"], 900)

    # ============================================================
    # DESATIVAÇÃO
    # ============================================================

    def test_desativar_item(self):
        resultado = cadastrar_item("Desodorante", 1500)

        desativacao = desativar_item(resultado["id"])

        self.assertTrue(desativacao["sucesso"])

        item = buscar_item(resultado["id"])

        self.assertEqual(item["ativo"], 0)

    def test_desativar_item_inexistente(self):
        resultado = desativar_item(9999)

        self.assertFalse(resultado["sucesso"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
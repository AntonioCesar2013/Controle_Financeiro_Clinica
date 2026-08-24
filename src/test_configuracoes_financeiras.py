import tempfile
import unittest
from pathlib import Path

from src import banco, configuracoes_financeiras


class TestConfiguracoesFinanceiras(unittest.TestCase):
    """Testa a leitura da configuração financeira."""

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

    def test_obter_configuracao_financeira_zerada(self):
        configuracao = configuracoes_financeiras.obter_configuracao()

        self.assertIsNotNone(configuracao)

        self.assertEqual(configuracao["aplicar_juros"], 0)
        self.assertEqual(configuracao["tipo_juros"], "PERCENTUAL")
        self.assertEqual(configuracao["valor_juros"], 0)

        self.assertEqual(configuracao["aplicar_multa"], 0)
        self.assertEqual(configuracao["tipo_multa"], "PERCENTUAL")
        self.assertEqual(configuracao["valor_multa"], 0)

        self.assertEqual(configuracao["ativo"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
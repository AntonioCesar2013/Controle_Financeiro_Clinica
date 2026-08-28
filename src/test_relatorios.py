import unittest

from src import relatorios


class RelatoriosTest(unittest.TestCase):
    def test_todas_as_areas_geram_estrutura_para_visualizacao(self):
        for tipo in relatorios.TIPOS:
            with self.subTest(tipo=tipo):
                resultado = relatorios.gerar(tipo, "2026-08-01", "2026-08-31")
                self.assertEqual(resultado["tipo"], tipo)
                self.assertTrue(resultado["titulo"])
                self.assertTrue(resultado["colunas"])
                self.assertIsInstance(resultado["linhas"], list)
                self.assertIsInstance(resultado["resumo"], list)

    def test_periodo_invertido_e_rejeitado(self):
        with self.assertRaises(ValueError):
            relatorios.gerar("financeiro", "2026-08-31", "2026-08-01")

    def test_tipo_desconhecido_e_rejeitado(self):
        with self.assertRaises(ValueError):
            relatorios.gerar("desconhecido")


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

import test_regressoes as base
from src.administracao import importacoes
from src.interface.servidor import Requisicao


class ImportacoesContasReceber(unittest.TestCase):
    def setUp(self):
        self.f = base.Regressoes()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        _, self.internacao_id = self.f.internar()

    def linha(self, parcela=10, **alteracoes):
        return {
            "internacao_id": self.internacao_id,
            "numero_parcela": parcela,
            "tipo": "MENSALIDADE",
            "data_vencimento": "2026-10-10",
            "valor": "1.500,00",
            "desconto": "50,00",
            **alteracoes,
        }

    def test_previa_nao_grava_e_confirmacao_grava_em_centavos(self):
        antes = self.f.sql("SELECT COUNT(*) FROM cobrancas")[0][0]
        previa = importacoes.processar_contas_receber([self.linha()])
        self.assertEqual((previa["novas"], previa["importadas"], previa["erros"]), (1, 0, []))
        self.assertEqual(self.f.sql("SELECT COUNT(*) FROM cobrancas")[0][0], antes)

        resultado = importacoes.processar_contas_receber([self.linha()], confirmar=True)
        self.assertEqual(resultado["importadas"], 1)
        self.assertEqual(
            self.f.sql("SELECT valor,desconto,status FROM cobrancas WHERE internacao_id=? AND numero_parcela=10",
                       (self.internacao_id,)),
            [(150000, 5000, "ABERTA")],
        )

    def test_duplicadas_sao_ignoradas(self):
        importacoes.processar_contas_receber([self.linha()], confirmar=True)
        resultado = importacoes.processar_contas_receber([self.linha()], confirmar=True)
        self.assertEqual((resultado["importadas"], resultado["duplicadas"]), (0, 1))

    def test_erro_impede_importacao_inteira(self):
        linhas = [self.linha(10), self.linha(11, valor="-1")]
        previa = importacoes.processar_contas_receber(linhas)
        self.assertEqual(len(previa["erros"]), 1)
        with self.assertRaisesRegex(ValueError, "Corrija os erros"):
            importacoes.processar_contas_receber(linhas, confirmar=True)
        self.assertEqual(self.f.sql("SELECT COUNT(*) FROM cobrancas WHERE numero_parcela>=10"), [(0,)])

    def test_api_aceita_previa_com_lista_de_linhas(self):
        req = object.__new__(Requisicao)
        req.path = "/api/administracao/importacoes/contas-receber"
        req._corpo_json = lambda: {"acao": "PREVIA", "linhas": [self.linha()]}
        with patch("src.interface.servidor.somente_leitura", return_value=False):
            resultado = self.f.post(req)
        self.assertTrue(resultado["sucesso"])
        self.assertEqual((resultado["novas"], resultado["importadas"]), (1, 0))


if __name__ == "__main__":
    unittest.main()

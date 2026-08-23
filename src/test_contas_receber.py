"""Testes do motor de consulta de contas a receber."""

import tempfile
import unittest
from pathlib import Path

from src import banco, recebimentos
from src.cobrancas import aplicar_desconto, gerar_cobrancas
from src.contas_receber import (
    buscar_cobranca_consolidada,
    listar_cobrancas_consolidadas,
)


class TestMotorContasReceber(unittest.TestCase):
    """Usa banco temporário para não alterar os dados da clínica."""

    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        self.caminho_original = banco.CAMINHO_BANCO
        self.caminho_recebimentos_original = recebimentos.CAMINHO_BANCO
        banco.CAMINHO_BANCO = Path(self.diretorio_temporario.name) / "clinica.db"
        recebimentos.CAMINHO_BANCO = banco.CAMINHO_BANCO
        banco.criar_tabelas()

    def tearDown(self):
        recebimentos.CAMINHO_BANCO = self.caminho_recebimentos_original
        banco.CAMINHO_BANCO = self.caminho_original
        self.diretorio_temporario.cleanup()

    def _criar_internacao(self, data_acolhimento="2026-05-22", valor_mensalidade=1500):
        conexao = banco.conectar()
        try:
            cursor = conexao.cursor()
            cursor.execute(
                "INSERT INTO residentes (nome, cpf) VALUES (?, ?)",
                ("Residente de teste", "11111111111"),
            )
            residente_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO responsaveis (nome, cpf) VALUES (?, ?)",
                ("Responsável de teste", "22222222222"),
            )
            responsavel_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO internacoes (
                    residente_id, responsavel_id, data_acolhimento,
                    periodo_tratamento, valor_contrato, valor_acolhimento,
                    valor_mensalidade
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    residente_id,
                    responsavel_id,
                    data_acolhimento,
                    1,
                    2500,
                    1000,
                    valor_mensalidade,
                ),
            )
            conexao.commit()
            return cursor.lastrowid
        finally:
            conexao.close()

    def _mensalidade(self):
        internacao_id = self._criar_internacao()
        self.assertTrue(gerar_cobrancas(internacao_id)["sucesso"])
        cobrancas = listar_cobrancas_consolidadas(internacao_id=internacao_id)
        return cobrancas[1]

    def test_cobranca_sem_recebimento(self):
        mensalidade = self._mensalidade()
        cobranca = buscar_cobranca_consolidada(mensalidade["id"], "2026-06-22")

        self.assertEqual(cobranca["data_vencimento"], "2026-06-22")
        self.assertEqual(cobranca["valor"], 1500)
        self.assertEqual(cobranca["desconto"], 0)
        self.assertEqual(cobranca["valor_devido"], 1500)
        self.assertEqual(cobranca["total_recebido"], 0)
        self.assertEqual(cobranca["saldo_restante"], 1500)
        self.assertIsNone(cobranca["data_pagamento"])
        self.assertEqual(cobranca["status"], "ABERTA")
        self.assertEqual(cobranca["situacao_temporal"], "PENDENTE")
        self.assertIsNone(cobranca["paga_em_atraso"])

        atrasada = buscar_cobranca_consolidada(mensalidade["id"], "2026-06-23")
        self.assertEqual(atrasada["situacao_temporal"], "ATRASADA")
        self.assertEqual(atrasada["data_vencimento"], "2026-06-22")

    def test_pagamento_integral_antes_do_vencimento(self):
        mensalidade = self._mensalidade()
        resultado = recebimentos.registrar_pagamento(
            mensalidade["id"], "2026-06-20", 1500, "PIX"
        )
        self.assertTrue(resultado["sucesso"])

        cobranca = buscar_cobranca_consolidada(mensalidade["id"], "2026-06-22")
        self.assertEqual(cobranca["status"], "PAGA")
        self.assertEqual(cobranca["total_recebido"], 1500)
        self.assertEqual(cobranca["saldo_restante"], 0)
        self.assertEqual(cobranca["data_pagamento"], "2026-06-20")
        self.assertEqual(cobranca["paga_em_atraso"], False)
        self.assertEqual(cobranca["data_vencimento"], "2026-06-22")
        self.assertEqual(cobranca["situacao_temporal"], "PAGA")

    def test_pagamento_integral_apos_vencimento(self):
        mensalidade = self._mensalidade()
        resultado = recebimentos.registrar_pagamento(
            mensalidade["id"], "2026-07-15", 1500, "PIX"
        )
        self.assertTrue(resultado["sucesso"])

        cobranca = buscar_cobranca_consolidada(mensalidade["id"], "2026-07-15")
        self.assertEqual(cobranca["total_recebido"], 1500)
        self.assertEqual(cobranca["saldo_restante"], 0)
        self.assertEqual(cobranca["data_pagamento"], "2026-07-15")
        self.assertEqual(cobranca["paga_em_atraso"], True)
        self.assertEqual(cobranca["data_vencimento"], "2026-06-22")
        self.assertEqual(cobranca["valor"], 1500)
        self.assertEqual(cobranca["status"], "PAGA")
        self.assertEqual(cobranca["situacao_temporal"], "PAGA")

    def test_multiplos_recebimentos(self):
        mensalidade = self._mensalidade()
        self.assertTrue(
            recebimentos.registrar_pagamento(
                mensalidade["id"], "2026-06-10", 500, "PIX"
            )["sucesso"]
        )
        self.assertTrue(
            recebimentos.registrar_pagamento(
                mensalidade["id"], "2026-06-20", 500, "PIX"
            )["sucesso"]
        )
        self.assertTrue(
            recebimentos.registrar_pagamento(
                mensalidade["id"], "2026-07-05", 500, "PIX"
            )["sucesso"]
        )

        cobranca = buscar_cobranca_consolidada(mensalidade["id"])
        self.assertEqual(cobranca["total_recebido"], 1500)
        self.assertEqual(cobranca["saldo_restante"], 0)
        self.assertEqual(cobranca["data_pagamento"], "2026-07-05")
        self.assertEqual(cobranca["data_vencimento"], "2026-06-22")
        self.assertEqual(cobranca["status"], "PAGA")
        self.assertEqual(cobranca["paga_em_atraso"], True)

    def test_recebimento_parcial(self):
        mensalidade = self._mensalidade()
        resultado = recebimentos.registrar_pagamento(
            mensalidade["id"], "2026-06-20", 500, "PIX"
        )
        self.assertTrue(resultado["sucesso"])

        cobranca = buscar_cobranca_consolidada(mensalidade["id"], "2026-06-23")
        self.assertEqual(cobranca["status"], "PARCIAL")
        self.assertEqual(cobranca["total_recebido"], 500)
        self.assertEqual(cobranca["saldo_restante"], 1000)
        self.assertEqual(cobranca["data_pagamento"], "2026-06-20")
        self.assertIsNone(cobranca["situacao_temporal"])
        self.assertIsNone(cobranca["paga_em_atraso"])
        self.assertEqual(cobranca["valor"], 1500)

    def test_cobranca_descontada_nao_vira_paga_nem_atrasada(self):
        mensalidade = self._mensalidade()
        resultado = aplicar_desconto(mensalidade["id"], 1500)
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["status"], "DESCONTADA")

        cobranca = buscar_cobranca_consolidada(mensalidade["id"], "2026-07-01")
        self.assertEqual(cobranca["status"], "DESCONTADA")
        self.assertIsNone(cobranca["situacao_temporal"])
        self.assertIsNone(cobranca["paga_em_atraso"])
        self.assertNotEqual(cobranca["status"], "PAGA")
        self.assertNotEqual(cobranca["situacao_temporal"], "ATRASADA")
        self.assertEqual(cobranca["valor"], 1500)
        self.assertEqual(cobranca["desconto"], 1500)
        self.assertEqual(cobranca["valor_devido"], 0)
        self.assertEqual(cobranca["total_recebido"], 0)
        self.assertEqual(cobranca["saldo_restante"], 0)
        self.assertEqual(cobranca["data_vencimento"], "2026-06-22")

    def test_consulta_nao_aplica_juros_nem_multa(self):
        mensalidade = self._mensalidade()
        recebimentos.registrar_pagamento(
            mensalidade["id"], "2026-07-15", 1500, "PIX"
        )
        cobranca = buscar_cobranca_consolidada(mensalidade["id"], "2026-07-15")

        self.assertNotIn("juros", cobranca)
        self.assertNotIn("multa", cobranca)
        self.assertEqual(cobranca["valor"], 1500)
        self.assertEqual(cobranca["saldo_restante"], 0)

        aberta = buscar_cobranca_consolidada(
            listar_cobrancas_consolidadas()[0]["id"], "2026-12-31"
        )
        self.assertNotIn("juros", aberta)
        self.assertNotIn("multa", aberta)
        self.assertEqual(aberta["valor"], 1000)

    def test_consulta_nao_altera_dados_persistidos(self):
        mensalidade = self._mensalidade()
        buscar_cobranca_consolidada(mensalidade["id"], "2026-07-01")

        conexao = banco.conectar()
        try:
            linha = conexao.execute(
                "SELECT data_vencimento, valor, desconto, status FROM cobrancas WHERE id = ?",
                (mensalidade["id"],),
            ).fetchone()
            recebidos = conexao.execute(
                "SELECT COUNT(*) FROM recebimentos WHERE cobranca_id = ?",
                (mensalidade["id"],),
            ).fetchone()[0]
        finally:
            conexao.close()

        self.assertEqual(linha[0], "2026-06-22")
        self.assertEqual(linha[1], 1500)
        self.assertEqual(linha[2], 0)
        self.assertEqual(linha[3], "ABERTA")
        self.assertEqual(recebidos, 0)

    def test_saldo_com_desconto_sem_recebimento(self):
        mensalidade = self._mensalidade()
        self.assertTrue(aplicar_desconto(mensalidade["id"], 200)["sucesso"])

        cobranca = buscar_cobranca_consolidada(mensalidade["id"])
        self.assertEqual(cobranca["valor"], 1500)
        self.assertEqual(cobranca["desconto"], 200)
        self.assertEqual(cobranca["valor_devido"], 1300)
        self.assertEqual(cobranca["total_recebido"], 0)
        self.assertEqual(cobranca["saldo_restante"], 1300)
        self.assertEqual(cobranca["status"], "ABERTA")

    def test_saldo_com_desconto_e_recebimento_parcial(self):
        mensalidade = self._mensalidade()
        self.assertTrue(aplicar_desconto(mensalidade["id"], 200)["sucesso"])
        self.assertTrue(
            recebimentos.registrar_pagamento(
                mensalidade["id"], "2026-06-20", 500, "PIX"
            )["sucesso"]
        )

        cobranca = buscar_cobranca_consolidada(mensalidade["id"])
        self.assertEqual(cobranca["valor"], 1500)
        self.assertEqual(cobranca["desconto"], 200)
        self.assertEqual(cobranca["valor_devido"], 1300)
        self.assertEqual(cobranca["total_recebido"], 500)
        self.assertEqual(cobranca["saldo_restante"], 800)
        self.assertEqual(cobranca["status"], "PARCIAL")
        self.assertIsNone(cobranca["situacao_temporal"])

    def test_saldo_zerado_quando_recebimento_igual_ao_devido(self):
        mensalidade = self._mensalidade()
        self.assertTrue(aplicar_desconto(mensalidade["id"], 200)["sucesso"])
        self.assertTrue(
            recebimentos.registrar_pagamento(
                mensalidade["id"], "2026-06-20", 1300, "PIX"
            )["sucesso"]
        )

        cobranca = buscar_cobranca_consolidada(mensalidade["id"])
        self.assertEqual(cobranca["valor"], 1500)
        self.assertEqual(cobranca["desconto"], 200)
        self.assertEqual(cobranca["valor_devido"], 1300)
        self.assertEqual(cobranca["total_recebido"], 1300)
        self.assertEqual(cobranca["saldo_restante"], 0)
        self.assertEqual(cobranca["status"], "PAGA")

    def test_saldo_nao_fica_negativo_quando_recebimento_excede_devido(self):
        mensalidade = self._mensalidade()
        self.assertTrue(aplicar_desconto(mensalidade["id"], 200)["sucesso"])

        conexao = banco.conectar()
        try:
            conexao.execute(
                """
                INSERT INTO recebimentos (
                    cobranca_id, data_recebimento, valor, forma_recebimento
                ) VALUES (?, ?, ?, ?)
                """,
                (mensalidade["id"], "2026-06-20", 1400, "PIX"),
            )
            conexao.commit()
        finally:
            conexao.close()

        cobranca = buscar_cobranca_consolidada(mensalidade["id"])
        self.assertEqual(cobranca["valor"], 1500)
        self.assertEqual(cobranca["desconto"], 200)
        self.assertEqual(cobranca["valor_devido"], 1300)
        self.assertEqual(cobranca["total_recebido"], 1400)
        self.assertEqual(cobranca["saldo_restante"], 0)
        self.assertGreaterEqual(cobranca["saldo_restante"], 0)

    def test_resumo_cobranca_usa_a_mesma_regra_de_saldo(self):
        mensalidade = self._mensalidade()
        self.assertTrue(aplicar_desconto(mensalidade["id"], 200)["sucesso"])
        self.assertTrue(
            recebimentos.registrar_pagamento(
                mensalidade["id"], "2026-06-20", 500, "PIX"
            )["sucesso"]
        )

        resumo = recebimentos.resumo_cobranca(mensalidade["id"])
        cobranca = buscar_cobranca_consolidada(mensalidade["id"])
        self.assertTrue(resumo["sucesso"])
        self.assertEqual(resumo["valor_cobranca"], cobranca["valor"])
        self.assertEqual(resumo["desconto"], cobranca["desconto"])
        self.assertEqual(resumo["valor_devido"], cobranca["valor_devido"])
        self.assertEqual(resumo["total_pago"], cobranca["total_recebido"])
        self.assertEqual(resumo["restante"], cobranca["saldo_restante"])
        self.assertEqual(resumo["restante"], 800)

    def test_listar_cobrancas_consolidadas(self):
        internacao_id = self._criar_internacao()
        gerar_cobrancas(internacao_id)
        lista = listar_cobrancas_consolidadas(
            internacao_id=internacao_id,
            data_referencia="2026-06-22",
        )
        self.assertEqual(len(lista), 2)
        self.assertEqual(lista[0]["tipo"], "ACOLHIMENTO")
        self.assertEqual(lista[1]["tipo"], "MENSALIDADE")
        self.assertIn("saldo_restante", lista[0])
        self.assertIn("valor_devido", lista[0])
        self.assertIn("paga_em_atraso", lista[0])

    def test_buscar_cobranca_inexistente(self):
        self.assertIsNone(buscar_cobranca_consolidada(9999))


if __name__ == "__main__":
    unittest.main(verbosity=2)

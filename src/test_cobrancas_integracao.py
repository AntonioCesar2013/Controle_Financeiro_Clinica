"""Testes de integração entre internações, cobranças e o motor de parcelas."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import banco, recebimentos
from src.cobrancas import gerar_cobrancas, listar_cobrancas
from src.parcelas import calcular_data_vencimento


class TestIntegracaoCobrancasParcelas(unittest.TestCase):
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

    def _criar_internacao(self, data_acolhimento, periodo_tratamento):
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
                    periodo_tratamento,
                    999999,
                    100000,
                    200000,
                ),
            )
            conexao.commit()
            return cursor.lastrowid
        finally:
            conexao.close()

    def _gerar_e_listar(self, data_acolhimento, periodo_tratamento):
        internacao_id = self._criar_internacao(data_acolhimento, periodo_tratamento)
        resultado = gerar_cobrancas(internacao_id)
        self.assertTrue(resultado["sucesso"])
        return listar_cobrancas(internacao_id)

    def test_fluxo_real_delega_vencimentos_ao_motor_e_persiste_resultado(self):
        internacao_id = self._criar_internacao("2026-05-22", 3)
        with patch(
            "src.cobrancas.calcular_data_vencimento",
            wraps=calcular_data_vencimento,
        ) as calcular_mock:
            resultado = gerar_cobrancas(internacao_id)

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(calcular_mock.call_count, 3)
        self.assertEqual(
            [chamada.args for chamada in calcular_mock.call_args_list],
            [("2026-05-22", 1), ("2026-05-22", 2), ("2026-05-22", 3)],
        )
        cobrancas = listar_cobrancas(internacao_id)
        self.assertEqual(
            [cobranca["data_vencimento"] for cobranca in cobrancas],
            ["2026-05-22", "2026-06-22", "2026-07-22", "2026-08-22"],
        )

    def test_dia_31_e_persistido_com_regra_do_motor(self):
        cobrancas = self._gerar_e_listar("2026-01-31", 4)
        self.assertEqual(
            [cobranca["data_vencimento"] for cobranca in cobrancas],
            ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31"],
        )

    def test_ano_bissexto_e_persistido_com_regra_do_motor(self):
        cobrancas = self._gerar_e_listar("2028-01-31", 3)
        self.assertEqual(
            [cobranca["data_vencimento"] for cobranca in cobrancas],
            ["2028-01-31", "2028-02-29", "2028-03-31", "2028-04-30"],
        )

    def test_cobranca_aberta_antes_do_vencimento_e_pendente(self):
        internacao_id = self._criar_internacao("2026-05-22", 1)
        gerar_cobrancas(internacao_id)

        mensalidade = listar_cobrancas(internacao_id, "2026-06-20")[1]

        self.assertEqual(mensalidade["status"], "ABERTA")
        self.assertEqual(mensalidade["situacao_temporal"], "PENDENTE")

    def test_cobranca_aberta_apos_vencimento_e_atrasada(self):
        internacao_id = self._criar_internacao("2026-05-22", 1)
        gerar_cobrancas(internacao_id)

        mensalidade = listar_cobrancas(internacao_id, "2026-06-23")[1]

        self.assertEqual(mensalidade["status"], "ABERTA")
        self.assertEqual(mensalidade["situacao_temporal"], "ATRASADA")

    def test_recebimento_total_torna_situacao_paga_sem_alterar_vencimento(self):
        internacao_id = self._criar_internacao("2026-05-22", 1)
        gerar_cobrancas(internacao_id)
        mensalidade = listar_cobrancas(internacao_id)[1]

        resultado = recebimentos.registrar_pagamento(
            mensalidade["id"],
            "2026-07-15",
            200000,
            "PIX",
            "Recebimento posterior ao vencimento",
        )

        self.assertTrue(resultado["sucesso"])
        cobranca_atualizada = listar_cobrancas(internacao_id, "2026-07-15")[1]
        self.assertEqual(cobranca_atualizada["status"], "PAGA")
        self.assertEqual(cobranca_atualizada["situacao_temporal"], "PAGA")
        self.assertEqual(cobranca_atualizada["data_vencimento"], "2026-06-22")
        self.assertEqual(cobranca_atualizada["data_pagamento"], "2026-07-15")

        conexao = banco.conectar()
        try:
            recebido = conexao.execute(
                "SELECT data_recebimento FROM recebimentos WHERE cobranca_id = ?",
                (mensalidade["id"],),
            ).fetchone()[0]
        finally:
            conexao.close()
        self.assertEqual(recebido, "2026-07-15")

    def test_status_parcial_nao_recebe_mapeamento_temporal(self):
        internacao_id = self._criar_internacao("2026-05-22", 1)
        gerar_cobrancas(internacao_id)
        mensalidade = listar_cobrancas(internacao_id)[1]

        resultado = recebimentos.registrar_pagamento(
            mensalidade["id"], "2026-06-20", 100000, "PIX"
        )

        self.assertTrue(resultado["sucesso"])
        cobranca_atualizada = listar_cobrancas(internacao_id, "2026-06-23")[1]
        self.assertEqual(cobranca_atualizada["status"], "PARCIAL")
        self.assertIsNone(cobranca_atualizada["situacao_temporal"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

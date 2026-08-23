"""Testes unitários do motor puro de parcelas."""

import unittest

from src.parcelas import (
    calcular_data_vencimento,
    calcular_status_parcela,
    criar_parcela,
    gerar_parcelas,
)


class TestMotorParcelas(unittest.TestCase):
    def test_primeira_parcela_um_mes_apos_acolhimento(self):
        vencimento = calcular_data_vencimento("2026-05-22", 1)
        self.assertEqual(vencimento.isoformat(), "2026-06-22")

    def test_gera_vencimentos_mensais_seguindo_o_mesmo_dia(self):
        parcelas = gerar_parcelas("2026-05-22", [1, 2, 3, 4])
        self.assertEqual(
            [parcela["data_vencimento"] for parcela in parcelas],
            ["2026-06-22", "2026-07-22", "2026-08-22", "2026-09-22"],
        )

    def test_parcela_nao_vencida_e_pendente(self):
        status = calcular_status_parcela("2026-06-22", data_referencia="2026-06-22")
        self.assertEqual(status, "PENDENTE")

    def test_parcela_sem_pagamento_apos_vencimento_e_atrasada(self):
        status = calcular_status_parcela("2026-06-22", data_referencia="2026-06-23")
        self.assertEqual(status, "ATRASADA")

    def test_parcela_com_data_pagamento_e_paga(self):
        status = calcular_status_parcela(
            "2026-06-22", data_pagamento="2026-06-25", data_referencia="2026-06-30"
        )
        self.assertEqual(status, "PAGA")

    def test_data_pagamento_e_vencimento_sao_campos_distintos(self):
        parcela = criar_parcela(
            "2026-05-22", 1, valor=125000, data_pagamento="2026-06-25", data_referencia="2026-06-30"
        )
        self.assertEqual(parcela["valor"], 125000)
        self.assertEqual(parcela["data_vencimento"], "2026-06-22")
        self.assertEqual(parcela["data_pagamento"], "2026-06-25")
        self.assertEqual(parcela["status"], "PAGA")

    def test_dia_base_31_usa_ultimo_dia_e_retorna_ao_dia_base(self):
        parcelas = gerar_parcelas("2026-01-31", [1, 2, 3, 4, 5])
        self.assertEqual(
            [parcela["data_vencimento"] for parcela in parcelas],
            ["2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31", "2026-06-30"],
        )

    def test_dia_base_31_em_ano_bissexto(self):
        parcelas = gerar_parcelas("2028-01-31", [1, 2, 3])
        self.assertEqual(
            [parcela["data_vencimento"] for parcela in parcelas],
            ["2028-02-29", "2028-03-31", "2028-04-30"],
        )

    def test_dia_base_30_nao_herda_ajuste_de_fevereiro(self):
        parcelas = gerar_parcelas("2026-01-30", [1, 2, 3, 4])
        self.assertEqual(
            [parcela["data_vencimento"] for parcela in parcelas],
            ["2026-02-28", "2026-03-30", "2026-04-30", "2026-05-30"],
        )

    def test_dia_base_29_em_ano_nao_bissexto(self):
        parcelas = gerar_parcelas("2026-01-29", [1, 2, 3])
        self.assertEqual(
            [parcela["data_vencimento"] for parcela in parcelas],
            ["2026-02-28", "2026-03-29", "2026-04-29"],
        )

    def test_dia_base_29_em_ano_bissexto(self):
        parcelas = gerar_parcelas("2028-01-29", [1, 2, 3])
        self.assertEqual(
            [parcela["data_vencimento"] for parcela in parcelas],
            ["2028-02-29", "2028-03-29", "2028-04-29"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

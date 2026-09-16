"""Dashboard e Visão Financeira usam a mesma consulta de movimentos recentes."""
import unittest

import test_regressoes as base_tests
from src.financeiro import caixa, contas_pagar, despesas, devolucoes, pagamentos, recebimentos
from src.interface.rotas.financeiro import rotas_get
from src.interface.servidor import _dashboard


class DashboardFinanceiro(unittest.TestCase):
    def setUp(self):
        self.f = base_tests.Regressoes()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_dashboard_vazio(self):
        painel = _dashboard()
        self.assertEqual(painel['movimentacoes_recentes'], [])
        self.assertEqual(painel['resultado'], 0)

    def test_dashboard_e_caixa_com_todas_as_origens(self):
        _, iid = self.f.internar()
        cid = self.f.sql('SELECT id FROM cobrancas WHERE internacao_id=? ORDER BY id', (iid,))[0][0]
        recebido = recebimentos.registrar_pagamento(cid, self.f.hoje, 1000)
        self.assertTrue(recebido['sucesso'], recebido)
        devolucao = devolucoes.registrar(recebido['id'], 200, self.f.hoje, 'PIX', 'Parcial', 'D1')
        self.assertTrue(devolucao['sucesso'], devolucao)
        sid = despesas.cadastrar_setor('Operacional')['id']
        did = despesas.cadastrar_despesa(sid, 'Teste', 'FIXA')['id']
        conta = contas_pagar.cadastrar_conta(did, self.f.hoje, 300)['id']
        self.assertTrue(pagamentos.registrar_pagamento(conta, self.f.hoje, 300)['sucesso'])
        self.f.sql("""INSERT INTO entradas_bancarias(data_entrada,valor,forma_recebimento,descricao,origem_documento)
                      VALUES(?,400,'PIX','Teste bancário','TESTE-1')""", (self.f.hoje,))
        movimentos = caixa.listar_movimentacoes(limite=10)
        self.assertEqual({m['origem'] for m in movimentos}, {'RECEBIMENTO', 'DEVOLUCAO', 'PAGAMENTO', 'BANCO'})
        self.assertEqual([m['data'] for m in movimentos], sorted(m['data'] for m in movimentos))
        dashboard = _dashboard()
        caixa_api = rotas_get({'data_inicio': [self.f.hoje], 'data_fim': [self.f.hoje]})['/api/caixa']()
        self.assertEqual(len(dashboard['movimentacoes_recentes']), 4)
        self.assertEqual(len(caixa_api['movimentacoes']), 4)
        self.assertEqual((dashboard['total_entradas'], dashboard['total_saidas'], dashboard['resultado']),
                         (1400, 500, 900))
        self.assertEqual((caixa_api['total_entradas'], caixa_api['total_saidas'], caixa_api['resultado']),
                         (1400, 500, 900))


if __name__ == '__main__':
    unittest.main()

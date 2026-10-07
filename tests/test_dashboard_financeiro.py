"""Dashboard e Visão Financeira usam a mesma consulta de movimentos recentes."""
import unittest
from datetime import date
from unittest.mock import patch

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

    def test_vencimentos_no_periodo_inclusivo_e_saldo_parcial(self):
        contas = [dict(data_vencimento=d, saldo_restante=v, status=s) for d,v,s in [
            ('2026-01-31', 900, 'ABERTA'), ('2026-02-01', 100, 'PARCIAL'),
            ('2026-02-28', 200, 'ABERTA'), ('2026-03-01', 800, 'ABERTA'),
            ('2026-02-15', 0, 'PAGA')]]
        with patch('src.interface.servidor.contas_receber.listar_cobrancas_consolidadas', return_value=contas):
            self.assertEqual(_dashboard('2026-02-01', '2026-02-28')['total_receber'], 300)
            self.assertEqual(_dashboard('2026-03-01', '2026-03-31')['total_receber'], 800)

    def test_padrao_mes_corrente_e_movimentos_fora_do_periodo(self):
        with patch('src.interface.servidor.date') as clock:
            clock.today.return_value = date(2026, 2, 10)
            self.assertEqual(_dashboard(), _dashboard('2026-02-01', '2026-02-28'))
        self.f.sql("""INSERT INTO entradas_bancarias(data_entrada,valor,forma_recebimento,descricao,origem_documento)
                      VALUES('2026-02-15',400,'PIX','Teste','PERIODO')""")
        sid = despesas.cadastrar_setor('Período')['id']
        did = despesas.cadastrar_despesa(sid, 'Teste', 'FIXA')['id']
        contas_pagar.cadastrar_conta(did, '2026-02-01', 300)
        contas_pagar.cadastrar_conta(did, '2026-03-01', 700)
        fevereiro = _dashboard('2026-02-01', '2026-02-28')
        marco = _dashboard('2026-03-01', '2026-03-31')
        self.assertEqual((fevereiro['total_pagar'], marco['total_pagar']), (300, 700))
        self.assertEqual((fevereiro['total_entradas'], marco['total_entradas']), (400, 0))
        self.assertEqual(len(fevereiro['movimentacoes_recentes']), 1)
        self.assertEqual(marco['movimentacoes_recentes'], [])
        with self.assertRaises(ValueError):
            _dashboard('2026-03-01', '2026-02-01')

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

    def test_dashboard_exibe_exatamente_as_dez_ultimas_movimentacoes(self):
        for indice in range(12):
            self.f.sql("""INSERT INTO entradas_bancarias(data_entrada,valor,forma_recebimento,descricao,origem_documento)
                          VALUES(?,100,'PIX',?,?)""", (self.f.hoje, f'Entrada {indice}', f'D-{indice}'))
        recentes = _dashboard(self.f.hoje, self.f.hoje)['movimentacoes_recentes']
        self.assertEqual(len(recentes), 10)
        self.assertEqual(recentes[0]['descricao'], '[Conciliação pendente] Entrada 11')
        self.assertEqual(recentes[-1]['descricao'], '[Conciliação pendente] Entrada 2')

    def test_caixa_paginado_limita_linhas_sem_alterar_totais(self):
        for indice in range(12):
            self.f.sql("""INSERT INTO entradas_bancarias(data_entrada,valor,forma_recebimento,descricao,origem_documento)
                          VALUES(?,100,'PIX',?,?)""", (self.f.hoje, f'Entrada {indice}', f'P-{indice}'))
        pagina = caixa.resumo_com_movimentacoes(self.f.hoje, self.f.hoje, pagina=1, tamanho=10)
        self.assertEqual(len(pagina['movimentacoes']['linhas']), 10)
        self.assertEqual(pagina['movimentacoes']['total_registros'], 12)
        self.assertEqual(pagina['total_entradas'], 1200)
        segunda = caixa.resumo_com_movimentacoes(self.f.hoje, self.f.hoje, pagina=2, tamanho=10)
        self.assertEqual(len(segunda['movimentacoes']['linhas']), 2)


if __name__ == '__main__':
    unittest.main()

"""Fluxos de saída, recorrência, prorrogação e estoque em banco descartável."""
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from unittest.mock import patch

import test_regressoes as fixtures
from src.infraestrutura import banco, operacoes
from src.cadastros import internacoes
from src.cantina import produtos, vendas
from src.financeiro import acertos, devolucoes, recorrencias, recebimentos, contas_receber, caixa, conferencia, recibos
from src.interface import extrato_residente, validacao


class Fluxos(unittest.TestCase):
    setUp = fixtures.Regressoes.setUp
    sql = fixtures.Regressoes.sql
    internar = fixtures.Regressoes.internar
    carteira = fixtures.Regressoes.carteira
    post = fixtures.Regressoes.post

    def test_produto_com_historico_nao_vira_servico_e_estorno_repoe(self):
        wid, pid = self.carteira()
        venda = vendas.registrar_compra(wid, [{'item_id': pid, 'quantidade': 20}])
        self.assertTrue(venda['sucesso'])
        self.assertFalse(produtos.editar_produto(pid, 'Teste', categoria='Serviço')['sucesso'])
        self.assertEqual(self.sql('SELECT estoque_atual FROM itens WHERE id=?', (pid,))[0][0], 0)
        self.assertTrue(vendas.estornar_compra(venda['id'])['sucesso'])
        self.assertEqual(self.sql('SELECT estoque_atual FROM itens WHERE id=?', (pid,))[0][0], 20)

    def test_servico_vendido_nao_vira_produto(self):
        wid, _ = self.carteira()
        pid = produtos.cadastrar_produto('Corte', 100, categoria='Serviço')['id']
        venda = vendas.registrar_venda(wid, pid)
        self.assertFalse(produtos.editar_produto(pid, 'Corte', categoria='Produto')['sucesso'])
        self.assertTrue(vendas.estornar_movimentacao(venda['id'])['sucesso'])
        self.assertEqual(self.sql('SELECT estoque_atual FROM itens WHERE id=?', (pid,))[0][0], 0)

    def test_item_sem_historico_pode_mudar(self):
        pid = produtos.cadastrar_produto('Novo', 100)['id']
        self.assertTrue(produtos.editar_produto(pid, 'Novo', categoria='Serviço')['sucesso'])

    def test_encerramento_particular_exige_escolha_e_preserva_se_manter(self):
        _, iid = self.internar()
        antes = self.sql('SELECT valor,desconto,status FROM cobrancas WHERE internacao_id=?', (iid,))
        self.assertFalse(internacoes.encerrar_internacao(iid, self.hoje)['sucesso'])
        d = acertos.previa(iid, self.hoje, 'MANTER')
        self.assertEqual(d['total_pendente'], 70000)
        self.assertTrue(internacoes.encerrar_internacao(iid, self.hoje, 'Saída', politica='MANTER', assinatura=d['assinatura'])['sucesso'])
        self.assertEqual(antes, self.sql('SELECT valor,desconto,status FROM cobrancas WHERE internacao_id=?', (iid,)))

    def test_devolucao_saida_e_encerramento_preservam_recibo_entrada_e_extrato(self):
        rid, iid = self.internar()
        cid = self.sql('SELECT id FROM cobrancas WHERE internacao_id=? AND numero_parcela=1', (iid,))[0][0]
        pago = recebimentos.registrar_pagamento(cid, self.hoje, 30000)
        recibo = recibos.gerar(pago['id'])
        d = acertos.previa(iid, self.hoje, 'DISPENSAR_FUTURAS')
        self.assertEqual(d['total_devolver'], 30000)
        self.assertFalse(internacoes.encerrar_internacao(iid, self.hoje, politica='DISPENSAR_FUTURAS')['sucesso'])
        devolucoes.registrar(pago['id'], 30000, self.hoje, 'PIX', 'Saída', 'PIX-123')
        self.assertEqual(self.sql('SELECT valor FROM recebimentos WHERE id=?', (pago['id'],))[0][0], 30000)
        self.assertFalse(internacoes.encerrar_internacao(iid, self.hoje, politica='DISPENSAR_FUTURAS', assinatura=d['assinatura'])['sucesso'])
        d = acertos.previa(iid, self.hoje, 'DISPENSAR_FUTURAS')
        self.assertTrue(internacoes.encerrar_internacao(iid, self.hoje, 'Dispensa acordada', politica='DISPENSAR_FUTURAS', assinatura=d['assinatura'])['sucesso'])
        self.assertEqual(contas_receber.buscar_cobranca_consolidada(cid)['saldo_restante'], 0)
        resumo = caixa.resumo_caixa(self.hoje, self.hoje)
        self.assertEqual((resumo['total_entradas'], resumo['total_saidas']), (30000, 30000))
        self.assertEqual(recibos.consultar(recibo['id'])['dados'], recibo['dados'])
        self.assertEqual(recibos.consultar(recibo['id'])['total_devolvido'], 30000)
        self.assertEqual(extrato_residente.consultar(rid)['resumo']['devolvido_periodo'], 30000)
        self.assertFalse(recebimentos.excluir_recebimento(pago['id'], 'Incorreto')['sucesso'])

    def test_devolucao_parcial_limites_e_recebimento_posterior(self):
        _, iid = self.internar()
        cid = self.sql('SELECT id FROM cobrancas WHERE internacao_id=? AND numero_parcela=0', (iid,))[0][0]
        pago = recebimentos.registrar_pagamento(cid, self.hoje, 10000)
        devolucoes.registrar(pago['id'], 3000, self.hoje, 'PIX', 'Acerto', 'D1')
        self.assertEqual(contas_receber.buscar_cobranca_consolidada(cid)['status'], 'PARCIAL')
        for valor, data in [(7001, self.hoje), (1, (date.today()+timedelta(days=1)).isoformat()), (1, '2020-01-01')]:
            with self.assertRaises(ValueError):
                devolucoes.registrar(pago['id'], valor, data, 'PIX', 'Acerto', 'D2')
        self.assertTrue(recebimentos.registrar_pagamento(cid, self.hoje, 3000)['sucesso'])
        self.assertEqual(recebimentos.resumo_cobranca(cid)['restante'], 0)

    def test_devolucao_carteira_inativa_separada_do_caixa(self):
        wid, _ = self.carteira()
        vendas.adicionar_credito(wid, 10000)
        vendas.alterar_status_carteira(wid, 0)
        vendas.devolver_saldo(wid, 10010, self.hoje, 'PIX', 'Saída', 'D1')
        with self.assertRaises(ValueError):
            vendas.devolver_saldo(wid, 1, self.hoje, 'PIX', 'Saída', 'D2')
        d = conferencia.mensal(self.hoje[:7])
        self.assertEqual(d['carteiras']['devolucoes'], 10010)
        self.assertEqual(d['carteiras']['compras'], 0)
        self.assertEqual(d['carteiras']['saldo_fechamento'], 0)
        self.assertEqual(caixa.resumo_caixa()['total_saidas'], 0)

    def programar(self):
        setor = self.sql("INSERT INTO setores(nome) VALUES('Geral')")
        despesa = self.sql("INSERT INTO despesas(setor_id,descricao,natureza,recorrente) VALUES(?,'Aluguel','FIXA',1)", (setor,))
        return recorrencias.configurar(despesa, 10000, '2026-01-31', '2026-04-30')['id']

    def test_recorrencia_fim_mes_concorrencia_e_cancelamento_nao_recria(self):
        rid = self.programar()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(lambda _: recorrencias.gerar(rid, '2026-12-31'), range(2)))
        self.assertEqual(sum(r['quantidade'] for r in resultados), 4)
        self.assertEqual(self.sql('SELECT data_vencimento FROM contas_pagar ORDER BY data_vencimento'), [('2026-01-31',), ('2026-02-28',), ('2026-03-31',), ('2026-04-30',)])
        self.sql("UPDATE contas_pagar SET status='CANCELADA'")
        self.assertEqual(recorrencias.gerar(rid, '2026-12-31')['quantidade'], 0)
        recorrencias.encerrar(rid)
        with self.assertRaises(ValueError): recorrencias.gerar(rid, '2026-12-31')

    def test_prorrogacao_preserva_pagamento_e_rejeita_repeticao(self):
        _, iid = self.internar()
        cid = self.sql('SELECT id FROM cobrancas WHERE internacao_id=? ORDER BY id', (iid,))[0][0]
        recebimentos.registrar_pagamento(cid, self.hoje, 10000)
        antes = self.sql('SELECT * FROM cobrancas WHERE internacao_id=? ORDER BY id', (iid,))
        r = internacoes.prorrogar_internacao(iid, 2, 4, 'Continuidade')
        self.assertEqual(r['cobrancas'], 2)
        self.assertEqual(self.sql('SELECT * FROM cobrancas WHERE internacao_id=? ORDER BY id LIMIT 3', (iid,)), antes)
        with self.assertRaises(ValueError): internacoes.prorrogar_internacao(iid, 2, 4, 'Reenvio')
        self.assertEqual(self.sql('SELECT valor_contrato FROM internacoes WHERE id=?', (iid,))[0][0], 130000)

    def test_prorrogacao_convenio_e_saida_sem_duplicar_diarias(self):
        _, iid = self.internar('2026-01-01', 'CONVENIO')
        antes = self.sql('SELECT * FROM cobrancas ORDER BY id')
        internacoes.prorrogar_internacao(iid, 2, 3, 'Mais um mês')
        self.assertEqual(self.sql('SELECT * FROM cobrancas ORDER BY id LIMIT 3'), antes)
        d = acertos.previa(iid, '2026-03-10')
        self.assertEqual(sum(c['valor_novo'] for c in d['cobrancas']), 69*10000)
        self.assertTrue(internacoes.encerrar_internacao(iid, '2026-03-10', 'Saída')['sucesso'])

    def test_prorrogacao_conflitante_nao_altera(self):
        rid, iid = self.internar('2026-01-01')
        self.assertTrue(internacoes.cadastrar_internacao_com_cobrancas(rid, 1, '2026-04-01', 2, 70000, 10000, 30000)['sucesso'])
        with self.assertRaises(ValueError): internacoes.prorrogar_internacao(iid, 2, 4, 'Conflito')
        self.assertEqual(self.sql('SELECT periodo_tratamento FROM internacoes WHERE id=?', (iid,))[0][0], 2)

    def test_saldo_parcial_atrasado_nao_muda_status_financeiro(self):
        _, iid = self.internar('2026-01-01')
        cid = self.sql('SELECT id FROM cobrancas WHERE internacao_id=? AND numero_parcela=1', (iid,))[0][0]
        recebimentos.registrar_pagamento(cid, '2026-02-01', 10000)
        d = contas_receber.buscar_cobranca_consolidada(cid, '2026-02-10')
        self.assertEqual((d['status'], d['situacao_temporal'], d['dias_atraso']), ('PARCIAL', 'ATRASADA', 9))

    def test_api_devolucao_converte_centavos_e_reenvio_nao_duplica(self):
        from src.interface.servidor import Requisicao
        wid, _ = self.carteira()
        vendas.adicionar_credito(wid, 1000)
        req = object.__new__(Requisicao)
        req.path = '/api/carteiras/devolver'
        req._corpo_json = lambda: {'carteira_id': wid, 'valor': '1,25', 'data_movimentacao': self.hoje,
                                   'forma_pagamento': 'PIX', 'motivo': 'Saída', 'documento': 'D1'}
        with patch('src.interface.servidor.somente_leitura', return_value=False):
            primeiro = self.post(req)
            segundo = req.do_POST()
        self.assertTrue(primeiro['sucesso'])
        self.assertEqual(primeiro['id'], segundo['id'])
        self.assertEqual(self.sql("SELECT valor_total FROM movimentacoes_carteira WHERE tipo='DEVOLUCAO'"), [(125,)])

    def test_devolucao_de_encargos_permite_cancelar_agendamento_pago(self):
        rid, iid = self.internar((date.today()+timedelta(days=10)).isoformat())
        cid = self.sql('SELECT id FROM cobrancas WHERE internacao_id=? ORDER BY id', (iid,))[0][0]
        pago = recebimentos.registrar_pagamento(cid, self.hoje, 10000, multa_juros=500)
        devolucoes.registrar(pago['id'], 10000, self.hoje, 'PIX', 'Cancelamento', 'D1')
        self.assertFalse(internacoes.cancelar_agendamento(iid, 'Cancelado')['sucesso'])
        devolucoes.registrar(pago['id'], 0, self.hoje, 'PIX', 'Devolver encargos', 'D2', multa_juros=500)
        self.assertTrue(internacoes.cancelar_agendamento(iid, 'Cancelado')['sucesso'])
        self.assertEqual(caixa.resumo_caixa()['resultado'], 0)
        self.assertEqual(self.sql('SELECT valor,multa_juros FROM recebimentos WHERE id=?', (pago['id'],)), [(10000, 500)])

    def test_api_programacao_prorrogacao_e_previa_obrigatoria(self):
        from src.interface.servidor import Requisicao
        req = object.__new__(Requisicao)
        def enviar(rota, dados):
            req.path = rota
            req._corpo_json = lambda: dados
            with patch('src.interface.servidor.somente_leitura', return_value=False):
                return self.post(req)
        _, iid = self.internar()
        r = enviar('/api/internacoes/prorrogar', {'id': iid, 'periodo_atual': '2', 'novo_periodo': '3', 'motivo': 'Continuidade'})
        self.assertTrue(r['sucesso'], r)
        dados = {'id': iid, 'data_encerramento': self.hoje, 'politica': 'MANTER', 'motivo': 'Saída'}
        self.assertFalse(enviar('/api/internacoes/encerrar', dados)['sucesso'])
        dados['assinatura'] = acertos.previa(iid, self.hoje, 'MANTER')['assinatura']
        self.assertTrue(enviar('/api/internacoes/encerrar', dados)['sucesso'])
        rid = self.programar()
        r = enviar('/api/recorrencias/gerar', {'id': rid, 'data_limite': '2026-04-30'})
        self.assertTrue(r['sucesso'], r)
        self.assertEqual(r['quantidade'], 4)

    def test_fechamento_antigo_sem_devolucoes_mantem_formato_da_assinatura(self):
        d = conferencia.mensal('2025-01')
        self.assertNotIn('devolucoes', d['carteiras'])
        esperado = {k: d[k] for k in ('competencia', 'inicio', 'fim', 'clinica', 'carteiras', 'banco', 'pendentes')}
        self.sql('''INSERT INTO fechamentos_mensais(competencia,revisao,responsavel,observacao,dados,assinatura)
            VALUES('2025-01',1,'Teste','Original',?,?)''', (conferencia.serializar(esperado), conferencia.assinatura(esperado)))
        banco.criar_tabelas()
        self.assertEqual(conferencia.mensal('2025-01')['historico'][0]['status'], 'FECHADO')


if __name__ == '__main__':
    unittest.main()

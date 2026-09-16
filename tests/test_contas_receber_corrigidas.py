"""Regressões de contas a receber em banco temporário."""
import json
import unittest
import uuid
from unittest.mock import patch

import test_regressoes as base_tests
from src.financeiro import cobrancas, devolucoes, recebimentos
from src.financeiro.estornos import historico, historico_ajustes
from src.interface.extrato_residente import consultar
from src.interface.rotas.financeiro import rotas_get
from src.interface.servidor import Requisicao


class ContasReceberCorrigidas(unittest.TestCase):
    def setUp(self):
        self.f = base_tests.Regressoes()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.residente, internacao = self.f.internar()
        self.ids = [r[0] for r in self.f.sql(
            'SELECT id FROM cobrancas WHERE internacao_id=? ORDER BY numero_parcela', (internacao,))]

    def post(self, rota, dados, chave=None):
        req = object.__new__(Requisicao)
        req.path = rota
        req._corpo_json = lambda: dados
        req.headers = {'Idempotency-Key': chave or uuid.uuid4().hex}
        req.client_address = ('127.0.0.1', 0)
        req.command = 'POST'
        req._sessao = lambda: None
        req._json = lambda payload, status=200, cookie=None: (payload, int(status), cookie) if req._capturando else ({**payload, 'sucesso': False} if status >= 400 else payload)
        with patch('src.interface.servidor.somente_leitura', return_value=False):
            return req.do_POST()

    def test_desconto_integral_parcial_historico_idempotencia(self):
        cid = self.ids[0]
        chave = uuid.uuid4().hex
        dados = {'cobranca_id': cid, 'valor': '100.00'}
        primeiro = self.post('/api/cobrancas/desconto', dados, chave)
        repetido = self.post('/api/cobrancas/desconto', dados, chave)
        self.assertTrue(primeiro.get('sucesso'), primeiro)
        self.assertEqual(repetido['status'], 'DESCONTADA')
        self.assertEqual(len(historico_ajustes(cid)), 1)
        ajuste = historico_ajustes(cid)[0]
        self.assertEqual((ajuste['valor_anterior'], ajuste['valor_novo'],
                          ajuste['desconto_anterior'], ajuste['desconto_novo']),
                         (10000, 10000, 0, 10000))
        self.assertIn('Desconto independente', ajuste['motivo'])
        conflito = self.post('/api/cobrancas/desconto', {'cobranca_id': cid, 'valor': '90.00'}, chave)
        self.assertFalse(conflito['sucesso'])
        self.assertEqual(len(historico_ajustes(cid)), 1)
        self.assertEqual(self.f.sql('SELECT COUNT(*) FROM recebimentos WHERE cobranca_id=?', (cid,))[0][0], 0)

        parcial = recebimentos.registrar_pagamento(self.ids[1], self.f.hoje, 1000)
        self.assertTrue(parcial['sucesso'], parcial)
        restante = self.post('/api/cobrancas/desconto', {'cobranca_id': self.ids[1], 'valor': '290.00'})
        self.assertTrue(restante['sucesso'], restante)
        self.assertEqual(restante['status'], 'PAGA')
        self.assertEqual(len(historico_ajustes(self.ids[1])), 1)
        self.assertEqual(self.f.sql('SELECT COUNT(*) FROM recebimentos WHERE cobranca_id=?', (self.ids[1],))[0][0], 1)
        self.assertFalse(self.post('/api/recebimentos', {'cobranca_id': self.ids[2],
            'data_pagamento': self.f.hoje, 'valor': '0', 'desconto': '300.00'})['sucesso'])

    def test_validacao_dominio_e_rollback(self):
        cid = self.ids[0]
        for valor in (0.5, True, None, '1', 0, -1, 9_000_000_000_000_001, 10001):
            self.assertFalse(cobrancas.aplicar_desconto(cid, valor)['sucesso'], valor)
        self.assertEqual(self.f.sql('SELECT desconto FROM cobrancas WHERE id=?', (cid,))[0][0], 0)
        self.assertEqual(historico_ajustes(cid), [])
        self.assertTrue(cobrancas.aplicar_desconto(cid, 1000)['sucesso'])
        self.assertFalse(cobrancas.aplicar_desconto(cid, 9001)['sucesso'])
        self.assertEqual(len(historico_ajustes(cid)), 1)

    def test_falha_do_historico_desfaz_desconto(self):
        cid = self.ids[0]
        self.f.sql("""CREATE TRIGGER falha_ajuste BEFORE INSERT ON ajustes_cobrancas
                      BEGIN SELECT RAISE(ABORT, 'Falha simulada'); END""")
        with self.assertRaisesRegex(Exception, 'Falha simulada'):
            cobrancas.aplicar_desconto(cid, 1000)
        self.assertEqual(self.f.sql('SELECT desconto,status FROM cobrancas WHERE id=?', (cid,))[0], (0, 'ABERTA'))
        self.assertEqual(historico_ajustes(cid), [])
        self.f.sql('DROP TRIGGER falha_ajuste')
        self.assertTrue(cobrancas.aplicar_desconto(cid, 1000)['sucesso'])

    def test_historico_compartilhado_saida_sem_encargos_legados(self):
        self.f.sql("""INSERT INTO estornos_financeiros
            (tabela,lancamento_id,origem_id,dados,motivo)
            VALUES('pagamentos_saida',999,1,?,'Correção')""", (json.dumps({'id': 999, 'valor': 1000}),))
        registro = historico('pagamentos_saida', 1, [
            {'id': 1, 'valor': 200, 'multa_juros': 30, 'total_lancamento': 230}])
        self.assertEqual([(r['total_lancamento'], r['estornada']) for r in registro],
                         [(230, False), (1000, True)])

    def test_estornos_total_original_caixa_e_legado(self):
        cid = self.ids[0]
        recebido = recebimentos.registrar_pagamento(cid, self.f.hoje, 1000, multa_juros=150)
        self.assertTrue(recebido['sucesso'], recebido)
        self.assertTrue(recebimentos.excluir_recebimento(recebido['id'], 'Erro')['sucesso'])
        historico = rotas_get({'id': [str(cid)]})['/api/contas-receber/recebimentos']()
        self.assertEqual((historico[0]['total_lancamento'], historico[0]['estornada']), (1150, True))
        self.assertEqual(consultar(self.residente)['resumo']['recebido_periodo'], 0)
        self.assertEqual(self.f.sql('SELECT COUNT(*) FROM recebimentos WHERE id=?', (recebido['id'],))[0][0], 0)
        # JSON legado sem a coluna de encargos.
        antigo = self.f.sql("SELECT id,dados FROM estornos_financeiros WHERE tabela='recebimentos'")[0]
        dados = json.loads(antigo[1]); dados.pop('multa_juros', None)
        self.f.sql('UPDATE estornos_financeiros SET dados=? WHERE id=?', (json.dumps(dados), antigo[0]))
        self.assertEqual(rotas_get({'id': [str(cid)]})['/api/contas-receber/recebimentos']()[0]['total_lancamento'], 1000)

    def test_extrato_devolucoes_mistas(self):
        p = recebimentos.registrar_pagamento(self.ids[0], self.f.hoje, 10000)
        d1 = devolucoes.registrar(p['id'], 400, self.f.hoje, 'PIX', 'Erro', 'D1')
        devolucoes.estornar(d1['id'], 'Registro equivocado')
        devolucoes.registrar(p['id'], 300, self.f.hoje, 'PIX', 'Parcial', 'D2')
        extrato = consultar(self.residente)
        self.assertEqual(extrato['resumo']['devolvido_periodo'], 300)
        self.assertEqual([r['estornada'] for r in extrato['devolucoes']], [1, 0])
        self.assertEqual(extrato['devolucoes'][0]['motivo_estorno'], 'Registro equivocado')


if __name__ == '__main__':
    unittest.main()

"""Regressões de contas a pagar com banco descartável."""
import unittest
import subprocess
from pathlib import Path
from urllib.parse import parse_qs

import test_regressoes as base_tests
from src.financeiro import contas_pagar, despesas, pagamentos, recorrencias
from src.interface.rotas.financeiro import rotas_get


class ContasPagarCorrigidas(unittest.TestCase):
    def setUp(self):
        self.fixture = base_tests.Regressoes()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.sid = despesas.cadastrar_setor('Operacional')['id']
        self.did = despesas.cadastrar_despesa(self.sid, 'Água', 'FIXA', True)['id']

    def conta(self, data, valor=20000):
        resultado = contas_pagar.cadastrar_conta(self.did, data, valor)
        self.assertTrue(resultado['sucesso'], resultado)
        return resultado['id']

    def test_filtro_api_e_totais_canceladas(self):
        janeiro = self.conta('2026-01-15', 10000)
        fevereiro = self.conta('2026-02-01', 20000)
        self.conta('2026-02-28', 30000)
        self.conta('2026-03-01', 40000)
        self.assertTrue(contas_pagar.cancelar_conta(janeiro)['sucesso'])
        cliente = subprocess.run(['node', str(Path(__file__).with_name('contas_pagar.mjs')), '--query'],
                                 check=True, capture_output=True, text=True)
        query = parse_qs(cliente.stdout.splitlines()[-1])
        query['tamanho'] = ['1']
        primeira = rotas_get(query)['/api/contas-pagar']()
        segunda = rotas_get({**query, 'pagina': ['2']})['/api/contas-pagar']()
        self.assertEqual(primeira['linhas'][0]['id'], fevereiro)
        self.assertNotEqual(primeira['linhas'][0]['id'], segunda['linhas'][0]['id'])
        self.assertEqual(primeira['total_filtrado'], 2)
        self.assertEqual(primeira['totais_filtrados']['restante'], 50000)
        self.assertEqual(primeira['totais_gerais']['restante'], 90000)
        parcial = rotas_get({'pagina': ['1'], 'data_inicio': ['2026-02-01']})['/api/contas-pagar']()
        self.assertEqual(parcial['total_filtrado'], 3)
        self.assertEqual(parcial['totais_filtrados']['restante'], 90000)
        canceladas = contas_pagar.listar_contas_paginadas(status='CANCELADA')
        self.assertEqual(canceladas['total_filtrado'], 1)
        self.assertEqual(canceladas['totais_filtrados']['valor'], 10000)
        self.assertEqual(canceladas['totais_filtrados']['restante'], 0)
        self.assertEqual(canceladas['linhas'][0]['valor'], 10000)

    def test_dispensa_considera_contas_manuais_geradas_e_canceladas(self):
        vencimento = '2026-02-15'
        manual = self.conta(vencimento)
        rid = recorrencias.configurar(self.did, 20000, vencimento, vencimento)['id']
        self.assertEqual(recorrencias.previa(rid, vencimento)['itens'][0]['situacao'], 'EXISTENTE')
        with self.assertRaisesRegex(ValueError, 'conta efetiva'):
            recorrencias.dispensar_competencia(rid, vencimento, 'Dispensa indevida')
        self.assertEqual(self.fixture.sql('SELECT COUNT(*) FROM recorrencias_competencias_dispensadas')[0][0], 0)
        pago = pagamentos.registrar_pagamento(manual, self.fixture.hoje, 5000)
        self.assertTrue(pago['sucesso'], pago)
        with self.assertRaisesRegex(ValueError, 'conta efetiva'):
            recorrencias.dispensar_competencia(rid, vencimento, 'Dispensa indevida')
        self.assertEqual(self.fixture.sql('SELECT COUNT(*) FROM recorrencias_competencias_dispensadas')[0][0], 0)
        self.fixture.sql("UPDATE contas_pagar SET status='CANCELADA' WHERE id=?", (manual,))
        self.assertEqual(recorrencias.previa(rid, vencimento)['itens'][0]['situacao'], 'CONTA_CANCELADA')
        self.assertTrue(recorrencias.dispensar_competencia(rid, vencimento, 'Cancelada')['sucesso'])
        self.assertEqual(recorrencias.previa(rid, vencimento)['itens'][0]['situacao'], 'DISPENSADA')

    def test_dispensa_gerada_multiplas_e_competencia_livre(self):
        outra_despesa = despesas.cadastrar_despesa(self.sid, 'Energia', 'FIXA', True)['id']
        vencimento = '2026-04-15'
        rid = recorrencias.configurar(outra_despesa, 10000, vencimento, vencimento)['id']
        geradas = recorrencias.gerar(rid, vencimento)
        self.assertEqual(geradas['quantidade'], 1)
        with self.assertRaisesRegex(ValueError, 'conta efetiva'):
            recorrencias.dispensar_competencia(rid, vencimento, 'Não pode')
        self.fixture.sql("INSERT INTO contas_pagar(despesa_id,data_vencimento,valor,status) VALUES(?,?,?,'ABERTA')",
                         (outra_despesa, vencimento, 10000))
        self.assertEqual(recorrencias.previa(rid, vencimento)['itens'][0]['situacao'], 'CONFLITO_MULTIPLAS_CONTAS')
        self.assertEqual(self.fixture.sql('SELECT COUNT(*) FROM recorrencias_competencias_dispensadas')[0][0], 0)
        livre = '2026-05-15'
        outra = despesas.cadastrar_despesa(self.sid, 'Internet', 'FIXA', True)['id']
        rid_livre = recorrencias.configurar(outra, 5000, livre, livre)['id']
        self.assertTrue(recorrencias.dispensar_competencia(rid_livre, livre, 'Sem conta')['sucesso'])
        self.assertEqual(recorrencias.previa(rid_livre, livre)['itens'][0]['situacao'], 'DISPENSADA')

    def test_resumo_recalculo_desconto_e_estorno(self):
        self.assertFalse(pagamentos.resumo_conta(99999)['sucesso'])
        conta = self.conta(self.fixture.hoje)
        self.assertEqual(pagamentos.resumo_conta(conta)['restante'], 20000)
        primeiro = pagamentos.registrar_pagamento(conta, self.fixture.hoje, 5000)
        self.assertTrue(primeiro['sucesso'])
        self.assertEqual(pagamentos.resumo_conta(conta)['restante'], 15000)
        segundo = pagamentos.registrar_pagamento(conta, self.fixture.hoje, 13000, valor_desconto=2000)
        self.assertTrue(segundo['sucesso'])
        recalculado = contas_pagar.atualizar_status_conta(conta)
        self.assertEqual((recalculado['status'], recalculado['restante']), ('PAGA', 0))
        self.assertEqual(pagamentos.resumo_conta(conta)['valor_devido'], 18000)
        self.assertTrue(pagamentos.excluir_pagamento(segundo['id'], 'Correção')['sucesso'])
        detalhe = contas_pagar.calcular_total_pago(conta)
        self.assertEqual(detalhe['restante'], 15000)

    def test_validacao_dominio_e_setor_inativo(self):
        inicial = self.fixture.sql('SELECT COUNT(*) FROM contas_pagar')[0][0]
        for data, valor in [('2026-02-30', 100), ('2026-2-01', 100), ('2026-02-01', True),
                            ('2026-02-01', 100.5), ('2026-02-01', 0), ('2026-02-01', -1),
                            ('2026-02-01', None), ('2026-02-01', 9_000_000_000_000_001)]:
            self.assertFalse(contas_pagar.cadastrar_conta(self.did, data, valor)['sucesso'])
        self.assertEqual(self.fixture.sql('SELECT COUNT(*) FROM contas_pagar')[0][0], inicial)
        antiga = self.conta(self.fixture.hoje)
        despesas.desativar_setor(self.sid)
        self.assertFalse(contas_pagar.cadastrar_conta(self.did, self.fixture.hoje, 1000)['sucesso'])
        self.assertTrue(pagamentos.registrar_pagamento(antiga, self.fixture.hoje, 1000)['sucesso'])


if __name__ == '__main__':
    unittest.main()

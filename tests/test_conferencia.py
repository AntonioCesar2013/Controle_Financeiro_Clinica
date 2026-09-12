import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.infraestrutura import banco
from src.financeiro import caixa, conciliacao, conferencia, recebimentos
from src.cantina import vendas
from src.interface.servidor import Requisicao


class Conferencia(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory(prefix='conferencia_clinica_')
        self.addCleanup(pasta.cleanup)
        p = patch.object(banco, 'CAMINHO_BANCO', Path(pasta.name) / 'teste.db')
        p.start()
        self.addCleanup(p.stop)
        banco.criar_tabelas()
        self.sql("INSERT INTO residentes(id,nome,cpf,ativo) VALUES(1,'Residente teste','1',1)")
        self.sql("INSERT INTO responsaveis(id,nome,cpf) VALUES(1,'Responsável','2')")
        self.sql("""INSERT INTO internacoes(id,residente_id,responsavel_id,data_acolhimento,
            periodo_tratamento,valor_contrato,valor_acolhimento,valor_mensalidade)
            VALUES(1,1,1,'2025-01-01',12,100000,0,100000)""")
        self.sql("INSERT INTO cobrancas(id,internacao_id,numero_parcela,tipo,data_vencimento,valor) VALUES(1,1,1,'MENSALIDADE','2025-01-10',100000)")
        self.sql("INSERT INTO carteiras(id,residente_id,saldo) VALUES(1,1,0)")
        self.sql("INSERT INTO itens(id,nome,ativo,estoque_atual) VALUES(1,'Produto',1,7)")

    def sql(self, query, args=()):
        with closing(banco.conectar()) as conn, conn:
            cur = conn.execute(query, args)
            return cur.fetchall() if cur.description else cur.lastrowid

    def entrada(self, valor=10000, data='2025-01-10'):
        return self.sql('INSERT INTO entradas_bancarias(data_entrada,descricao,valor,origem_documento) VALUES(?,?,?,?)',
                        (data, 'Transferência '+str(self.sql('SELECT COUNT(*) FROM entradas_bancarias')[0][0]), valor, 'Extrato teste'))

    def receber(self, valor=10000, data='2025-01-10'):
        resultado = recebimentos.registrar_pagamento(1, data, valor)
        self.assertTrue(resultado['sucesso'])
        return resultado['id']

    def credito(self, valor=10000):
        self.assertTrue(vendas.adicionar_credito(1, valor, '2025-01-10')['sucesso'])
        return self.sql('SELECT MAX(id) FROM movimentacoes_carteira')[0][0]

    def fechar(self):
        d = conferencia.mensal('2025-01')
        return conferencia.fechar('2025-01', d['assinatura'], 'Operador', 'Documentos conferidos', {
            'entradas': d['clinica']['entradas'], 'saidas': d['clinica']['saidas'],
            'creditos': d['carteiras']['creditos'], 'compras': d['carteiras']['compras'],
            'saldo_carteiras': d['carteiras']['saldo_fechamento'],
        })

    def test_conciliar_varios_recebimentos_uma_vez_e_desfazer_com_historico(self):
        eid = self.entrada()
        ids = [self.receber(4000), self.receber(6000)]
        self.assertEqual(caixa.resumo_caixa()['total_entradas'], 20000)
        r = conciliacao.conciliar(eid, 'RECEBIMENTO', ids, 'Extrato e recibos conferidos')
        self.assertEqual(caixa.resumo_caixa()['total_entradas'], 10000)
        with self.assertRaises(ValueError):
            conciliacao.conciliar(eid, 'RECEBIMENTO', ids, 'Repetição')
        recusado = recebimentos.excluir_recebimento(ids[0], 'Teste')
        self.assertFalse(recusado['sucesso'])
        self.assertIn('conciliação', recusado['erro'])
        conciliacao.desfazer(r['id'], 'Vínculo errado')
        self.assertEqual(caixa.resumo_caixa()['total_entradas'], 20000)
        self.assertTrue(recebimentos.excluir_recebimento(ids[0], 'Estorno após desfazer')['sucesso'])
        hist = conciliacao.painel()['historico'][0]
        self.assertEqual(hist['motivo_desfazer'], 'Vínculo errado')
        self.assertEqual(len(json.loads(hist['vinculos_originais'])), 2)

    def test_credito_conciliado_separado_e_correcao_reverte_transacao(self):
        eid, mid = self.entrada(), self.credito()
        r = conciliacao.conciliar(eid, 'CARTEIRA', [mid], 'Depósito da carteira')
        self.assertEqual(caixa.resumo_caixa()['total_entradas'], 0)
        self.assertEqual(conferencia.mensal('2025-01')['carteiras']['creditos'], 10000)
        resultado = vendas.corrigir_credito(mid, 20000, motivo='Teste')
        self.assertFalse(resultado['sucesso'])
        self.assertEqual(self.sql('SELECT saldo FROM carteiras')[0][0], 10000)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM movimentacoes_carteira')[0][0], 1)
        conciliacao.desfazer(r['id'], 'Corrigir valor')
        self.assertTrue(vendas.corrigir_credito(mid, 20000, motivo='Correção documentada')['sucesso'])

    def test_datas_diferentes_usam_data_bancaria_no_caixa(self):
        eid = self.entrada(data='2025-02-01')
        rid = self.receber(data='2025-01-31')
        conciliacao.conciliar(eid, 'RECEBIMENTO', [rid], 'Compensação no mês seguinte')
        self.assertEqual(caixa.resumo_mensal(2025, 1)['total_entradas'], 0)
        self.assertEqual(caixa.resumo_mensal(2025, 2)['total_entradas'], 10000)

    def test_divergencia_de_soma_e_vinculo_reutilizado_nao_gravam(self):
        eid, rid = self.entrada(), self.receber(5000)
        with self.assertRaises(ValueError):
            conciliacao.conciliar(eid, 'RECEBIMENTO', [rid], 'Soma errada')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM conciliacoes_bancarias')[0][0], 0)
        outro = self.entrada(5000)
        conciliacao.conciliar(outro, 'RECEBIMENTO', [rid], 'Conferido')
        with self.assertRaises(ValueError):
            conciliacao.conciliar(eid, 'RECEBIMENTO', [rid], 'Reutilizar')
        with self.assertRaises(ValueError):
            conciliacao.conciliar(eid, 'OUTRA_RECEITA', [], ' ')

    def test_conciliacoes_concorrentes_nao_duplicam(self):
        eid, rid = self.entrada(), self.receber()
        def executar(_):
            try:
                return conciliacao.conciliar(eid, 'RECEBIMENTO', [rid], 'Conferido')['sucesso']
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(executar, range(2))), [False, True])
        self.assertEqual(caixa.resumo_caixa()['total_entradas'], 10000)

    def test_saldos_preservam_divergencias_sem_alterar_dados(self):
        d = conferencia.saldos()
        valores = {r['chave']: r['valor'] for r in d['itens']}
        valores['ESTOQUE:1'] = 5
        r = conferencia.conferir_saldos(d['assinatura'], valores, 'Operador', 'Contagem física')
        self.assertEqual(r['status'], 'DIVERGENTE')
        self.assertEqual(self.sql('SELECT estoque_atual FROM itens')[0][0], 7)
        historico = conferencia.saldos()['historico'][0]
        self.assertEqual(next(r for r in historico['dados']['itens'] if r['tipo']=='ESTOQUE')['diferenca'], -2)
        valores['ESTOQUE:1'] = 7
        self.assertEqual(conferencia.conferir_saldos(d['assinatura'], valores, 'Operador', 'Recontagem')['status'], 'CONFERIDA')

    def test_saldos_desatualizados_ou_incompletos_recusados(self):
        d = conferencia.saldos()
        with self.assertRaises(ValueError):
            conferencia.conferir_saldos(d['assinatura'], {}, 'Operador', 'Documentos')
        self.credito()
        with self.assertRaises(ValueError):
            conferencia.conferir_saldos(d['assinatura'], {r['chave']:r['valor'] for r in d['itens']}, 'Operador', 'Documentos')

    def test_fechamento_bloqueia_pendencias_e_detecta_ajuste_posterior(self):
        eid = self.entrada()
        with self.assertRaises(ValueError):
            self.fechar()
        conciliacao.conciliar(eid, 'OUTRA_RECEITA', [], 'Doação sem cobrança')
        primeiro = self.fechar()
        self.assertEqual(conferencia.mensal('2025-01')['historico'][0]['status'], 'FECHADO')
        self.receber(5000)
        d = conferencia.mensal('2025-01')
        self.assertEqual(d['historico'][0]['status'], 'REVISAR')
        self.assertEqual(d['historico'][0]['dados']['clinica']['entradas'], 10000)
        with self.assertRaises(ValueError):
            self.fechar()
        conferencia.reabrir(primeiro['id'], 'Recebimento retroativo conferido')
        self.assertEqual(self.fechar()['revisao'], 2)
        self.assertEqual(len(conferencia.mensal('2025-01')['historico']), 2)

    def test_fechamento_recusa_totais_diferentes_e_mes_atual(self):
        from datetime import date
        d = conferencia.mensal('2025-01')
        with self.assertRaises(ValueError):
            conferencia.fechar('2025-01', d['assinatura'], 'Operador', 'Documentos',
                              {'entradas':1,'saidas':0,'creditos':0,'compras':0,'saldo_carteiras':0})
        mes = date.today().strftime('%Y-%m')
        d = conferencia.mensal(mes)
        with self.assertRaises(ValueError):
            conferencia.fechar(mes, d['assinatura'], 'Operador', 'Documentos', {})

    def test_fechamento_recusa_tela_desatualizada(self):
        d = conferencia.mensal('2025-01')
        self.receber(1000)
        with self.assertRaisesRegex(ValueError, 'movimentos mudaram'):
            conferencia.fechar('2025-01', d['assinatura'], 'Operador', 'Documentos',
                              {'entradas':0,'saidas':0,'creditos':0,'compras':0,'saldo_carteiras':0})
        self.assertEqual(self.sql('SELECT COUNT(*) FROM fechamentos_mensais')[0][0], 0)

    def test_migracao_repetida_preserva_conciliacao_e_fechamento(self):
        eid, rid = self.entrada(), self.receber()
        conciliacao.conciliar(eid, 'RECEBIMENTO', [rid], 'Extrato')
        self.fechar()
        banco.criar_tabelas()
        self.assertEqual(caixa.resumo_caixa()['total_entradas'], 10000)
        self.assertEqual(conferencia.mensal('2025-01')['historico'][0]['status'], 'FECHADO')

    def test_saldo_negativo_carteira_e_estorno_alteram_revisao(self):
        self.credito(1000)
        self.sql("INSERT INTO movimentacoes_carteira(carteira_id,tipo,valor_total,data_movimentacao) VALUES(1,'COMPRA',-1500,'2025-01-15')")
        self.sql('UPDATE carteiras SET saldo=-500 WHERE id=1')
        d = conferencia.mensal('2025-01')
        self.assertEqual(d['carteiras']['compras'], 1500)
        self.assertEqual(d['carteiras']['saldo_fechamento'], -500)
        self.fechar()
        self.sql("UPDATE movimentacoes_carteira SET estornada=1 WHERE tipo='COMPRA'")
        self.sql('UPDATE carteiras SET saldo=1000 WHERE id=1')
        self.assertEqual(conferencia.mensal('2025-01')['historico'][0]['status'], 'REVISAR')

    def test_api_http_converte_moeda_e_registra_conferencia(self):
        servidor = ThreadingHTTPServer(('127.0.0.1', 0), Requisicao)
        t = threading.Thread(target=servidor.serve_forever, daemon=True)
        t.start()
        self.addCleanup(t.join, 2)
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        url = f'http://127.0.0.1:{servidor.server_port}'
        with urlopen(url+'/api/conferencia/saldos') as r:
            d = json.load(r)['dados']
        valores = {r['chave']: str(r['valor']) if r['tipo']=='ESTOQUE' else str(r['valor']/100) for r in d['itens']}
        payload = {'assinatura':d['assinatura'],'responsavel':'Operador','observacao':'Conferido','valores':valores}
        with patch('src.interface.servidor.somente_leitura', return_value=False):
            with urlopen(Request(url+'/api/conferencia/saldos', json.dumps(payload).encode(), {'Content-Type':'application/json', 'Idempotency-Key':'teste_conferencia_http_001'})) as r:
                self.assertEqual(json.load(r)['status'], 'CONFERIDA')
            payload['valores']['CARTEIRA:1']=''
            with self.assertRaises(HTTPError) as erro:
                urlopen(Request(url+'/api/conferencia/saldos', json.dumps(payload).encode(), {'Content-Type':'application/json'}))
            self.assertEqual(erro.exception.code, 400)


if __name__ == '__main__':
    unittest.main()

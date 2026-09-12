"""Regressões da segunda revisão, sempre em bancos temporários."""
import unittest
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import test_regressoes as fixtures
from src.cadastros import internacoes, contatos
from src.cantina import vendas, produtos
from src.financeiro import recebimentos, pagamentos, despesas, contas_pagar, devolucoes, caixa, contas_receber


class Complementares(unittest.TestCase):
    setUp = fixtures.Regressoes.setUp
    sql = fixtures.Regressoes.sql
    internar = fixtures.Regressoes.internar
    carteira = fixtures.Regressoes.carteira
    post = fixtures.Regressoes.post

    def test_recebimento_futuro_nao_quita(self):
        _, iid = self.internar()
        cid = self.sql('SELECT id FROM cobrancas WHERE internacao_id=?', (iid,))[0][0]
        futuro = (date.today()+timedelta(days=1)).isoformat()
        self.assertFalse(recebimentos.registrar_pagamento(cid, futuro, 10000)['sucesso'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM recebimentos')[0][0], 0)
        self.assertTrue(recebimentos.registrar_pagamento(cid, self.hoje, 10000)['sucesso'])

    def test_pagamento_futuro_nao_baixa_conta(self):
        sid = despesas.cadastrar_setor('Setor futuro')['id']
        did = despesas.cadastrar_despesa(sid, 'Conta futura', 'FIXA')['id']
        cid = contas_pagar.cadastrar_conta(did, self.hoje, 10000)['id']
        futuro = (date.today()+timedelta(days=1)).isoformat()
        self.assertFalse(pagamentos.registrar_pagamento(cid, futuro, 10000)['sucesso'])
        self.assertEqual(self.sql('SELECT status FROM contas_pagar WHERE id=?', (cid,))[0][0], 'ABERTA')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM pagamentos_saida')[0][0], 0)

    def test_venda_futura_nao_movimenta(self):
        wid, pid = self.carteira()
        futuro = (date.today()+timedelta(days=1)).isoformat()
        self.assertFalse(vendas.registrar_compra(wid, [{'item_id': pid, 'quantidade': 1}], futuro)['sucesso'])
        self.assertFalse(vendas.registrar_venda(wid, pid, 1, futuro)['sucesso'])
        self.assertEqual(self.sql('SELECT saldo FROM carteiras')[0][0], 10)
        self.assertEqual(self.sql('SELECT estoque_atual FROM itens')[0][0], 20)

    def test_venda_anterior_ao_acolhimento_recusada(self):
        wid, pid = self.carteira()
        self.sql("UPDATE itens_valores SET data_inicio_valor='2020-01-01'")
        ontem = (date.today()-timedelta(days=1)).isoformat()
        self.assertFalse(vendas.registrar_venda(wid, pid, 1, ontem)['sucesso'])

    def test_venda_em_internacao_cancelada_ou_encerrada_recusada(self):
        wid, pid = self.carteira()
        self.sql("UPDATE itens_valores SET data_inicio_valor='2020-01-01'")
        iid = self.sql('SELECT id FROM internacoes')[0][0]
        self.sql("UPDATE internacoes SET encerrada_em=?,status='ENCERRADA' WHERE id=?", (self.hoje, iid))
        self.assertFalse(vendas.registrar_compra(wid, [{'item_id': pid, 'quantidade': 1}], self.hoje)['sucesso'])
        self.sql("UPDATE internacoes SET encerrada_em=NULL,status='CANCELADA' WHERE id=?", (iid,))
        self.assertFalse(vendas.registrar_compra(wid, [{'item_id': pid, 'quantidade': 1}], self.hoje)['sucesso'])

    def test_nova_internacao_nao_duplica_principal(self):
        rid, _ = self.internar('2026-01-01')
        rp = self.sql("INSERT INTO responsaveis(nome,cpf) VALUES('Segundo','22222222222')")
        self.assertTrue(internacoes.cadastrar_internacao_com_cobrancas(rid, rp, self.hoje, 2, 70000, 10000, 30000)['sucesso'])
        self.assertLessEqual(self.sql('SELECT COUNT(*) FROM residente_responsavel WHERE residente_id=? AND principal=1', (rid,))[0][0], 1)

    def test_agendamento_nao_troca_contato_e_ambiguidade_exige_escolha(self):
        rid, _ = self.internar()
        original = self.sql('SELECT responsavel_id FROM residente_responsavel WHERE residente_id=? AND principal=1', (rid,))[0][0]
        rp = self.sql("INSERT INTO responsaveis(nome,cpf) VALUES('Futuro','33333333333')")
        inicio = (date.today()+timedelta(days=100)).isoformat()
        self.assertTrue(internacoes.cadastrar_internacao_com_cobrancas(rid, rp, inicio, 1, 40000, 10000, 30000)['sucesso'])
        self.assertEqual(self.sql('SELECT responsavel_id FROM residente_responsavel WHERE residente_id=? AND principal=1', (rid,))[0][0], original)
        # Simula dado legado ambíguo anterior à restrição e exige escolha explícita.
        self.sql('DROP TRIGGER contato_principal_unico_update')
        self.sql('UPDATE residente_responsavel SET principal=1 WHERE residente_id=?', (rid,))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM residente_responsavel WHERE residente_id=? AND principal=1', (rid,))[0][0], 2)
        contatos.definir(rid, rp, 'Contato informado pela família')
        self.assertEqual(self.sql('SELECT responsavel_id FROM residente_responsavel WHERE residente_id=? AND principal=1', (rid,)), [(rp,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM historico_contatos_principais')[0][0], 1)

    def test_setor_inativo_recusa_conta_mas_aceita_pagamento_antigo(self):
        sid = despesas.cadastrar_setor('Setor')['id']
        did = despesas.cadastrar_despesa(sid, 'Despesa', 'FIXA')['id']
        cid = contas_pagar.cadastrar_conta(did, self.hoje, 10000)['id']
        despesas.desativar_setor(sid)
        self.assertFalse(contas_pagar.cadastrar_conta(did, self.hoje, 10000)['sucesso'])
        self.assertTrue(pagamentos.registrar_pagamento(cid, self.hoje, 10000)['sucesso'])

    def test_estorno_devolucao_tratamento_preserva_historico_e_recalcula(self):
        _, iid = self.internar()
        cid = self.sql('SELECT id FROM cobrancas WHERE internacao_id=? AND numero_parcela=1', (iid,))[0][0]
        pago = recebimentos.registrar_pagamento(cid, self.hoje, 30000, multa_juros=500)
        d = devolucoes.registrar(pago['id'], 10000, self.hoje, 'PIX', 'Devolução', 'D1', 500)
        self.assertEqual(caixa.resumo_caixa(self.hoje, self.hoje)['resultado'], 20000)
        r = devolucoes.estornar(d['id'], 'Valor devolvido cadastrado por engano')
        self.assertEqual((r['status'], r['saldo_restante']), ('PAGA', 0))
        self.assertEqual(caixa.resumo_caixa(self.hoje, self.hoje)['resultado'], 30500)
        registro = devolucoes.listar(cid)[0]
        self.assertEqual((registro['estornada'], registro['motivo_estorno']), (1, 'Valor devolvido cadastrado por engano'))
        with self.assertRaises(ValueError): devolucoes.estornar(d['id'], 'Duplicado')

    def test_estorno_devolucao_bloqueado_apos_dispensa_contratual(self):
        _, iid = self.internar()
        cid = self.sql('SELECT id FROM cobrancas WHERE internacao_id=? AND numero_parcela=1', (iid,))[0][0]
        pago = recebimentos.registrar_pagamento(cid, self.hoje, 30000)
        d = devolucoes.registrar(pago['id'], 30000, self.hoje, 'PIX', 'Saída', 'D1')
        from src.financeiro import acertos
        previa = acertos.previa(iid, self.hoje, 'DISPENSAR_FUTURAS')
        self.assertTrue(internacoes.encerrar_internacao(iid, self.hoje, 'Dispensa', politica='DISPENSAR_FUTURAS', assinatura=previa['assinatura'])['sucesso'])
        with self.assertRaises(ValueError): devolucoes.estornar(d['id'], 'Tentativa posterior')
        self.assertEqual(devolucoes.listar(cid)[0]['estornada'], 0)

    def test_estorno_devolucao_carteira_e_concorrencia(self):
        wid, _ = self.carteira()
        d = vendas.devolver_saldo(wid, 10, self.hoje, 'PIX', 'Saída', 'D1')
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(lambda _: vendas.estornar_movimentacao(d['id'], 'Correção'), range(2)))
        self.assertEqual(sum(bool(r['sucesso']) for r in resultados), 1)
        self.assertEqual(self.sql('SELECT saldo FROM carteiras WHERE id=?', (wid,))[0][0], 10)
        self.assertEqual(self.sql("SELECT estornada FROM movimentacoes_carteira WHERE id=?", (d['id'],)), [(1,)])

    def test_estorno_devolucao_marca_fechamento_anterior_para_revisao(self):
        _, iid = self.internar('2025-01-01')
        cid = self.sql('SELECT id FROM cobrancas WHERE internacao_id=? AND numero_parcela=0', (iid,))[0][0]
        pago = recebimentos.registrar_pagamento(cid, '2025-01-01', 10000)
        d = devolucoes.registrar(pago['id'], 1000, '2025-01-02', 'PIX', 'Devolução', 'D1')
        from src.financeiro import conferencia
        mes = conferencia.mensal('2025-01')
        valores = {'entradas': mes['clinica']['entradas'], 'saidas': mes['clinica']['saidas'],
                   'creditos': mes['carteiras']['creditos'], 'compras': mes['carteiras']['compras'],
                   'saldo_carteiras': mes['carteiras']['saldo_fechamento']}
        conferencia.fechar('2025-01', mes['assinatura'], 'Teste', 'Documentos', valores)
        devolucoes.estornar(d['id'], 'Lançamento incorreto')
        self.assertEqual(conferencia.mensal('2025-01')['historico'][0]['status'], 'REVISAR')

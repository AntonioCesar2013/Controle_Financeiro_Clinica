"""Reproduções dos defeitos atuais em banco temporário, sem dados reais."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / 'tests')]
from test_regressoes import Regressoes
from src.financeiro import cobrancas, recebimentos, devolucoes
from src.financeiro.estornos import historico_ajustes
from src.interface import extrato_residente
from src.interface.rotas.financeiro import rotas_get
from src.interface.servidor import Requisicao


def executar():
    f = Regressoes()
    f.setUp()
    resultados = {}
    def post(rota, dados):
        req = object.__new__(Requisicao)
        req.path = rota
        req._corpo_json = lambda: dados
        with patch('src.interface.servidor.somente_leitura', return_value=False):
            return f.post(req)
    try:
        rid, iid = f.internar()
        ids = [r[0] for r in f.sql('SELECT id FROM cobrancas WHERE internacao_id=? ORDER BY numero_parcela', (iid,))]
        p = recebimentos.registrar_pagamento(ids[0], f.hoje, 1000, multa_juros=150)
        assert p['sucesso']
        assert recebimentos.excluir_recebimento(p['id'], 'Correção de teste')['sucesso']
        h = rotas_get({'id': [str(ids[0])]})['/api/contas-receber/recebimentos']()[0]
        assert h['estornada'] and h['valor'] == 1000 and h['multa_juros'] == 150 and 'total_lancamento' not in h
        resultados['historico_estornado_sem_total'] = h
        p = recebimentos.registrar_pagamento(ids[1], f.hoje, 1000)
        d = devolucoes.registrar(p['id'], 400, f.hoje, 'PIX', 'Teste', 'D-1')
        assert devolucoes.estornar(d['id'], 'Devolução registrada por engano')['sucesso']
        extrato = extrato_residente.consultar(rid)
        assert extrato['resumo']['devolvido_periodo'] == 0 and extrato['devolucoes'][0]['estornada'] == 1
        resultados['extrato_devolucao_estornada'] = {'total_efetivo': extrato['resumo']['devolvido_periodo'], 'linha': extrato['devolucoes'][0]}
        desconto = post('/api/cobrancas/desconto', {'cobranca_id': ids[2], 'valor': '10.00'})
        assert desconto['sucesso'] and desconto['desconto'] == 1000, desconto
        assert historico_ajustes(ids[2]) == []
        resultados['desconto_sem_historico_da_cobranca'] = {'retorno': desconto, 'ajustes': historico_ajustes(ids[2])}
        fracionado = cobrancas.aplicar_desconto(ids[2], 0.5)
        assert fracionado['sucesso'], fracionado
        persistido = f.sql('SELECT desconto,typeof(desconto) FROM cobrancas WHERE id=?', (ids[2],))[0]
        assert persistido == (1000.5, 'real'), persistido
        resultados['desconto_fracionario_dominio'] = persistido
        recusado = post('/api/recebimentos', {'cobranca_id': ids[0], 'data_pagamento': f.hoje, 'valor': '0', 'desconto': '100.00'})
        assert not recusado['sucesso'], recusado
        integral = post('/api/cobrancas/desconto', {'cobranca_id': ids[0], 'valor': '100.00'})
        assert integral['sucesso'] and integral['status'] == 'DESCONTADA', integral
        resultados['desconto_integral_so_rota_propria'] = {'recebimento_zero': recusado, 'rota_desconto': integral}
        _, outro_iid = f.internar()
        outro_cid = f.sql('SELECT id FROM cobrancas WHERE internacao_id=? AND numero_parcela=0', (outro_iid,))[0][0]
        assert cobrancas.aplicar_desconto(outro_cid, 9970)['sucesso']
        exato = post('/api/recebimentos', {'cobranca_id': outro_cid, 'data_pagamento': f.hoje, 'valor': '0.10', 'desconto': '0.20'})
        assert exato['sucesso'] and exato['restante'] == 0 and exato['status'] == 'PAGA', exato
        resultados['soma_decimal_valida_aceita_pela_api'] = exato
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    finally:
        f.doCleanups()


if __name__ == '__main__':
    executar()

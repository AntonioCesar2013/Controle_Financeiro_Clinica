"""Confirma os defeitos da auditoria em bancos descartáveis, sem dados reais.

Execute: python docs/reproduzir_auditoria_contas_pagar_2026_09_16.py
As asserções descrevem os defeitos atuais, não critérios de aceite da correção.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / 'tests')]
from test_regressoes import Regressoes
from src.financeiro import contas_pagar, pagamentos, despesas, recorrencias
from src.interface.rotas.financeiro import rotas_get
from src.interface.servidor import Requisicao


def executar():
    fixture = Regressoes()
    fixture.setUp()
    resultados = {}
    def post(rota, dados):
        req = object.__new__(Requisicao)
        req.path = rota
        req._corpo_json = lambda: dados
        with patch('src.interface.servidor.somente_leitura', return_value=False):
            return fixture.post(req)
    try:
        sid = despesas.cadastrar_setor('Auditoria')['id']
        did = despesas.cadastrar_despesa(sid, 'Despesa teste', 'FIXA', True)['id']
        jan = contas_pagar.cadastrar_conta(did, '2026-01-15', 10000)['id']
        fev = contas_pagar.cadastrar_conta(did, '2026-02-15', 20000)['id']

        query_ui = {'pagina': ['1'], 'inicio': ['2026-02-01'], 'fim': ['2026-02-28']}
        atual = rotas_get(query_ui)['/api/contas-pagar']()
        correto = rotas_get({'pagina': ['1'], 'data_inicio': ['2026-02-01'], 'data_fim': ['2026-02-28']})['/api/contas-pagar']()
        assert atual['total_filtrado'] == 2 and correto['total_filtrado'] == 1
        resultados['filtros_de_vencimento'] = {'query_frontend': query_ui, 'retornadas': atual['total_filtrado'], 'esperadas': correto['total_filtrado']}

        assert contas_pagar.cancelar_conta(jan)['sucesso']
        lista = contas_pagar.listar_contas_paginadas()
        assert lista['totais_filtrados']['restante'] == 30000
        exigivel = sum(c['restante'] for c in lista['linhas'] if c['status'] != 'CANCELADA')
        assert exigivel == 20000
        resultados['cancelada_no_total'] = {'restante_exibido_centavos': 30000, 'exigivel_centavos': exigivel}

        rid = recorrencias.configurar(did, 20000, '2026-02-15', '2026-02-15')['id']
        antes = recorrencias.previa(rid, '2026-02-15')['itens'][0]
        assert antes['situacao'] == 'EXISTENTE' and antes['conta_id'] == fev
        dispensada = post('/api/recorrencias/dispensar', {'id': rid, 'data_vencimento': '2026-02-15', 'motivo': 'Teste de dispensa'})
        assert dispensada['sucesso'], dispensada
        depois = recorrencias.previa(rid, '2026-02-15')['itens'][0]
        saldo = contas_pagar.calcular_total_pago(fev)
        assert depois['situacao'] == 'DISPENSADA' and saldo['restante'] == 20000 and saldo['status'] == 'ABERTA'
        resultados['dispensa_com_conta_manual_efetiva'] = {'antes': antes, 'depois': depois, 'saldo_conta': saldo}

        try:
            pagamentos.resumo_conta(fev)
        except NameError as erro:
            resultados['resumo_conta'] = f'{type(erro).__name__}: {erro}'
        else:
            raise AssertionError('O NameError esperado não ocorreu')

        pago = pagamentos.registrar_pagamento(fev, fixture.hoje, 18000, valor_desconto=2000)
        assert pago['sucesso'] and pago['status'] == 'PAGA', pago
        recalculado = contas_pagar.atualizar_status_conta(fev)
        assert recalculado['status'] == 'PARCIAL' and recalculado['restante'] == 2000, recalculado
        detalhe = contas_pagar.calcular_total_pago(fev)
        assert detalhe['restante'] == 0 and detalhe['status'] == 'PARCIAL'
        resultados['recalculo_ignora_desconto'] = {'recalculado': recalculado, 'detalhe': detalhe}

        invalida = contas_pagar.cadastrar_conta(did, '2026-02-30', 100.5)
        assert invalida['sucesso'], invalida
        gravado = fixture.sql('SELECT data_vencimento,valor,typeof(valor) FROM contas_pagar WHERE id=?', (invalida['id'],))[0]
        assert gravado == ('2026-02-30', 100.5, 'real'), gravado
        rejeitado_api = post('/api/contas-pagar', {'despesa_id': did, 'data_vencimento': '2026-02-30', 'valor': '1.00'})
        assert not rejeitado_api['sucesso'], rejeitado_api
        resultados['validacao_ausente_no_dominio'] = {'persistido': gravado, 'api_rejeita_data': rejeitado_api['erro']}

        despesas.desativar_setor(sid)
        ofertadas = despesas.listar_despesas(False)
        assert next(d for d in ofertadas if d['id'] == did)['ativo'] == 1
        recusada = contas_pagar.cadastrar_conta(did, fixture.hoje, 10000)
        assert not recusada['sucesso'], recusada
        resultados['setor_inativo'] = {'despesa_continua_ativa': True, 'gravacao': recusada}
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    executar()

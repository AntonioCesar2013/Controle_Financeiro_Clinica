"""Reproduz achados em banco temporário; não acessa dados/clinica.db.

Execute na raiz: python docs/reproduzir_auditoria_cadastros_2026_09_16.py
As asserções confirmam o comportamento defeituoso encontrado nesta revisão.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / 'tests')]
from test_regressoes import Regressoes
from src.interface.servidor import Requisicao
from src.cadastros import residentes, responsaveis, internacoes, vigencia
from src.infraestrutura import banco
from contextlib import closing


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
        rid = residentes.cadastrar_residente('Residente teste', '12345678901', 'Cidade')['id']
        dados = dict(residente_id=str(rid), responsavel_id='1', data_acolhimento=fixture.hoje,
                     periodo_tratamento='', modalidade='VOLUNTARIO', convenio_id='',
                     valor_contrato='0.00', valor_acolhimento='0', valor_mensalidade='0',
                     servicos_voluntario='Atividades de apoio')
        r = post('/api/internacoes', dados)
        assert not r['sucesso'] and 'periodo_tratamento' in r['erro'], r
        resultados['voluntario_periodo_vazio'] = r
        for tipo, modulo, criar, editar, extras in [
            ('residente', residentes, 'cadastrar_residente', 'editar_residente', ['Cidade']),
            ('responsavel', responsaveis, 'cadastrar_responsavel', 'editar_responsavel', ['11999999999', None]),
        ]:
            criado = getattr(modulo, criar)('Nome teste', 'PENDENTE-TESTE', *extras)
            assert criado['sucesso'], criado
            alterado = getattr(modulo, editar)(criado['id'], 'Nome corrigido', 'PENDENTE-TESTE', *extras)
            assert not alterado['sucesso'], alterado
            resultados[f'pendente_{tipo}'] = alterado
            duplicado = getattr(modulo, criar)('Outro nome descartado', 'PENDENTE-TESTE', *extras)
            assert duplicado['sucesso'] and duplicado['existe'] and duplicado['nome'] == 'Nome teste', duplicado
            resultados[f'duplicado_{tipo}'] = duplicado
        r = post('/api/responsaveis/editar', dict(id=1, nome='Responsavel teste', cpf='00000000001', ativo='false'))
        assert not r['sucesso'] and 'Situação' in r['erro'], r
        resultados['booleano_textual_responsavel'] = r
        r = post('/api/convenios', dict(nome='Convenio booleano', valor_diaria='10', ativo='true'))
        assert not r['sucesso'], r
        resultados['booleano_textual_convenio'] = r
        iid = internacoes.cadastrar_internacao_com_cobrancas(rid, 1, fixture.hoje, 2, 0, 0, 0, 'SOCIAL')['id']
        r = internacoes.encerrar_internacao(iid, fixture.hoje, 'Saida para teste')
        assert r['sucesso'], r
        with closing(banco.conectar()) as conn:
            vigente = vigencia.possui_internacao_vigente(conn, rid, fixture.hoje)
        assert not vigente
        nova = internacoes.cadastrar_internacao_com_cobrancas(rid, 1, fixture.hoje, 2, 0, 0, 0, 'SOCIAL')
        assert not nova['sucesso'] and 'coincidente' in nova['erro'], nova
        resultados['reinternacao_no_dia_da_saida'] = dict(vigente_no_dia=vigente, nova=nova)
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    executar()

"""Regressões de cadastros com o banco real isolado por fixture temporária."""
import unittest
from contextlib import closing
from datetime import date, timedelta
from unittest.mock import patch

import test_regressoes as base_tests
from src.cadastros import internacoes, residentes, responsaveis, vigencia
from src.infraestrutura import banco
from src.interface.servidor import Requisicao


class CadastrosCorrigidos(unittest.TestCase):
    def setUp(self):
        self.fixture = base_tests.Regressoes()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def post(self, rota, dados):
        req = object.__new__(Requisicao)
        req.path = rota
        req._corpo_json = lambda: dados
        with patch('src.interface.servidor.somente_leitura', return_value=False):
            return self.fixture.post(req)

    def test_voluntario_do_formulario_e_demais_modalidades(self):
        rid = residentes.cadastrar_residente('Voluntário', '12345678901', 'Cidade')['id']
        payload = dict(residente_id=str(rid), responsavel_id='1', data_acolhimento=self.fixture.hoje,
                       modalidade='VOLUNTARIO', periodo_tratamento='', convenio_id='999',
                       valor_contrato='123', valor_acolhimento='23', valor_mensalidade='50',
                       servicos_voluntario='Atividades de apoio')
        resposta = self.post('/api/internacoes', payload)
        self.assertTrue(resposta['sucesso'], resposta)
        self.assertEqual(resposta['cobrancas'], 0)
        self.assertEqual(self.fixture.sql('SELECT periodo_tratamento,valor_contrato,convenio_id FROM internacoes WHERE id=?', (resposta['id'],))[0], (0, 0, None))
        outro = residentes.cadastrar_residente('Outro', '12345678902', 'Cidade')['id']
        for modalidade in ('PARTICULAR', 'SOCIAL', 'CONVENIO'):
            invalido = self.post('/api/internacoes', {**payload, 'residente_id': outro, 'modalidade': modalidade})
            self.assertFalse(invalido['sucesso'])
            self.assertIn('período', invalido['erro'].lower())
        self.assertEqual(self.fixture.sql('SELECT COUNT(*) FROM internacoes')[0][0], 1)

    def test_documento_pendente_edicao_regularizacao_e_duplicado(self):
        for modulo, criar, editar, extras in (
            (residentes, residentes.cadastrar_residente, residentes.editar_residente, ('Cidade',)),
            (responsaveis, responsaveis.cadastrar_responsavel, responsaveis.editar_responsavel, ('11999999999', None)),
        ):
            criado = criar('Original', 'PENDENTE-TESTE', *extras)
            self.assertTrue(criado['sucesso'])
            repetido = criar('Outro nome', 'PENDENTE-TESTE', *extras)
            self.assertTrue(repetido['existe'])
            self.assertEqual(repetido['nome'], 'Original')
            editado = editar(criado['id'], 'Corrigido', 'PENDENTE-TESTE', *extras)
            self.assertTrue(editado['sucesso'], editado)
            negado = editar(criado['id'], 'Invalido', 'PENDENTE-OUTRO', *extras)
            self.assertFalse(negado['sucesso'])
            regular = editar(criado['id'], 'Regular', '11111111111', *extras)
            self.assertTrue(regular['sucesso'], regular)
            self.assertFalse(editar(criado['id'], 'Voltar', 'PENDENTE-TESTE', *extras)['sucesso'])

    def test_booleanos_aceitos_e_invalidos_sem_gravacao(self):
        for indice, (entrada, esperado) in enumerate(((True, 1), (False, 0), (1, 1), (0, 0), ('1', 1), ('0', 0), ('true', 1), ('false', 0))):
            resposta = self.post('/api/responsaveis/editar', dict(id=1, nome='Responsavel teste', cpf='00000000001', ativo=entrada))
            self.assertTrue(resposta['sucesso'], resposta)
            self.assertEqual(self.fixture.sql('SELECT ativo FROM responsaveis WHERE id=1')[0][0], esperado)
            convenio = self.post('/api/convenios', dict(nome=f'Convenio {indice}', valor_diaria='10', ativo=entrada))
            self.assertTrue(convenio['sucesso'], convenio)
            self.assertEqual(self.fixture.sql('SELECT ativo FROM convenios WHERE id=?', (convenio['id'],))[0][0], esperado)
        for entrada in ('yes', 2, None, ''):
            resposta = self.post('/api/convenios', dict(nome='Não gravar', valor_diaria='10', ativo=entrada))
            self.assertFalse(resposta['sucesso'])
            self.assertIn('ativo', resposta['erro'])
        self.assertEqual(self.fixture.sql("SELECT COUNT(*) FROM convenios WHERE nome='Não gravar'")[0][0], 0)

    def test_reinternacao_na_saida_e_contato_preservado(self):
        rid = residentes.cadastrar_residente('Teste', '23456789012', 'Cidade')['id']
        inicio = (date.today() - timedelta(days=5)).isoformat()
        saida = (date.today() - timedelta(days=2)).isoformat()
        primeira = internacoes.cadastrar_internacao_com_cobrancas(rid, 1, inicio, 2, 0, 0, 0, 'SOCIAL')
        self.assertTrue(primeira['sucesso'], primeira)
        self.assertTrue(internacoes.encerrar_internacao(primeira['id'], saida, 'Saída')['sucesso'])
        with closing(banco.conectar()) as conn:
            self.assertFalse(vigencia.possui_internacao_vigente(conn, rid, saida))
        anterior = internacoes.cadastrar_internacao_com_cobrancas(rid, 1, (date.fromisoformat(saida)-timedelta(days=1)).isoformat(), 1, 0, 0, 0, 'SOCIAL')
        self.assertFalse(anterior['sucesso'])
        segunda = internacoes.cadastrar_internacao_com_cobrancas(rid, 1, saida, 1, 0, 0, 0, 'SOCIAL')
        self.assertTrue(segunda['sucesso'], segunda)
        self.assertEqual(self.fixture.sql('SELECT COUNT(*) FROM cobrancas WHERE internacao_id=?', (primeira['id'],))[0][0], 0)

    def test_responsavel_contratual_nao_altera_contato_e_exige_ativo(self):
        rid = residentes.cadastrar_residente('Residente', '34567890123', 'Cidade')['id']
        segundo = responsaveis.cadastrar_responsavel('Segundo', '45678901234', None, None)['id']
        internacao = internacoes.cadastrar_internacao_com_cobrancas(rid, segundo, self.fixture.hoje, 2, 0, 0, 0, 'SOCIAL')
        self.assertTrue(internacao['sucesso'], internacao)
        self.assertEqual(self.fixture.sql('SELECT responsavel_id FROM residente_responsavel WHERE residente_id=? AND principal=1', (rid,))[0][0], segundo)
        self.assertTrue(internacoes.alterar_responsavel_principal(internacao['id'], segundo)['sucesso'])
        self.assertEqual(self.fixture.sql('SELECT responsavel_id FROM internacoes WHERE id=?', (internacao['id'],))[0][0], segundo)
        self.assertTrue(internacoes.alterar_responsavel_principal(internacao['id'], 1)['sucesso'])
        self.assertEqual(self.fixture.sql('SELECT responsavel_id FROM residente_responsavel WHERE residente_id=? AND principal=1', (rid,))[0][0], segundo)
        self.fixture.sql('UPDATE responsaveis SET ativo=0 WHERE id=?', (segundo,))
        self.assertFalse(internacoes.alterar_responsavel_principal(internacao['id'], segundo)['sucesso'])
        self.assertEqual(self.fixture.sql('SELECT responsavel_id FROM internacoes WHERE id=?', (internacao['id'],))[0][0], 1)


if __name__ == '__main__':
    unittest.main()

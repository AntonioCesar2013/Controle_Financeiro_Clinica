"""Cadastro de pertences por residente em banco descartável."""
import unittest
import sqlite3
from datetime import date, timedelta
from unittest.mock import patch

import test_regressoes as base_tests
from src.cadastros import itens_residentes
from src.cadastros.modulo import _datas_itens_residentes
from src.infraestrutura import banco
from src.interface.rotas.cadastros import rotas_get
from src.interface.servidor import Requisicao


class ItensResidentes(unittest.TestCase):
    def setUp(self):
        self.f = base_tests.Regressoes()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.r1, _ = self.f.internar()
        self.r2, _ = self.f.internar()

    def post(self, rota, dados):
        req = object.__new__(Requisicao)
        req.path = rota
        req._corpo_json = lambda: dados
        with patch('src.interface.servidor.somente_leitura', return_value=False):
            return self.f.post(req)

    def test_migracao_idempotente_e_relacao_um_para_muitos(self):
        banco.criar_tabelas()
        self.assertEqual(self.f.sql("SELECT COUNT(*) FROM migracoes_schema WHERE modulo='cadastros' AND versao=3")[0][0], 1)
        self.assertEqual(self.f.sql("SELECT COUNT(*) FROM migracoes_schema WHERE modulo='cadastros' AND versao=4")[0][0], 1)
        a = itens_residentes.cadastrar(self.r1, 'Mala', 1, 'Azul')
        b = itens_residentes.cadastrar(self.r1, 'Sapato', 2)
        c = itens_residentes.cadastrar(self.r2, 'Relógio', 1)
        self.assertEqual([i['id'] for i in itens_residentes.listar(self.r1)], [a['id'], b['id']])
        self.assertEqual([i['id'] for i in itens_residentes.listar(self.r2)], [c['id']])
        banco.criar_tabelas()
        self.assertEqual(len(itens_residentes.listar(self.r1)), 2)
        self.assertEqual(self.f.sql("SELECT COUNT(*) FROM migracoes_schema WHERE modulo='cadastros' AND versao=3")[0][0], 1)

    def test_migracao_preserva_item_antigo_sem_inventar_data(self):
        with sqlite3.connect(':memory:') as conexao:
            conexao.execute('CREATE TABLE itens_residentes(id INTEGER PRIMARY KEY,residente_id INTEGER,nome TEXT)')
            conexao.execute("INSERT INTO itens_residentes(residente_id,nome) VALUES(1,'Mala antiga')")
            _datas_itens_residentes(conexao)
            _datas_itens_residentes(conexao)
            self.assertEqual(conexao.execute(
                'SELECT nome,data_entrada,data_retirada FROM itens_residentes').fetchone(),
                ('Mala antiga', None, None))

    def test_api_cadastro_edicao_e_consulta(self):
        criado = self.post('/api/residentes/itens', {'residente_id': self.r1, 'nome': '  Mala  ',
                                                     'quantidade': '2', 'descricao': '  Azul  ',
                                                     'data_entrada': self.f.hoje})
        self.assertTrue(criado['sucesso'], criado)
        item_id = criado['id']
        listado = rotas_get({'residente_id': [str(self.r1)]})['/api/residentes/itens']()
        self.assertEqual((listado[0]['nome'], listado[0]['quantidade'], listado[0]['descricao']),
                         ('Mala', 2, 'Azul'))
        self.assertEqual((listado[0]['data_entrada'], listado[0]['data_retirada']), (self.f.hoje, None))
        editado = self.post('/api/residentes/itens/editar', {'id': item_id, 'residente_id': self.r1,
                                                             'nome': 'Mala de mão', 'quantidade': 1,
                                                             'data_entrada': self.f.hoje, 'data_retirada': self.f.hoje})
        self.assertTrue(editado['sucesso'], editado)
        self.assertEqual(itens_residentes.listar(self.r1)[0]['nome'], 'Mala de mão')
        self.assertEqual(itens_residentes.listar(self.r1)[0]['data_retirada'], self.f.hoje)
        self.assertTrue(self.post('/api/residentes/itens/editar', {'id': item_id, 'nome': 'Mala de mão',
            'quantidade': 1, 'data_entrada': self.f.hoje, 'data_retirada': ''})['sucesso'])
        self.assertIsNone(itens_residentes.listar(self.r1)[0]['data_retirada'])
        self.assertEqual(itens_residentes.listar(self.r2), [])

    def test_validacoes_e_integridade(self):
        for dados in ({'residente_id': 99999, 'nome': 'Mala', 'quantidade': 1},
                      {'residente_id': self.r1, 'nome': ' ', 'quantidade': 1},
                      {'residente_id': self.r1, 'nome': 'Mala', 'quantidade': 0},
                      {'residente_id': self.r1, 'nome': 'Mala', 'quantidade': 1.5}):
            self.assertFalse(self.post('/api/residentes/itens', dados)['sucesso'])
        self.assertEqual(itens_residentes.listar(self.r1), [])
        with self.assertRaises(Exception):
            self.f.sql("INSERT INTO itens_residentes(residente_id,nome,quantidade) VALUES(99999,'Óculos',1)")
        criado = itens_residentes.cadastrar(self.r1, 'Óculos', 1)
        self.assertEqual(itens_residentes.listar(self.r1)[0]['data_entrada'], date.today().isoformat())
        with self.assertRaises(ValueError):
            itens_residentes.editar(criado['id'], '', 2)
        ontem = (date.today() - timedelta(days=1)).isoformat()
        amanha = (date.today() + timedelta(days=1)).isoformat()
        for entrada, retirada in ((amanha, None), ('2026-02-30', None), (self.f.hoje, amanha),
                                  (self.f.hoje, ontem)):
            self.assertFalse(self.post('/api/residentes/itens/editar', {'id': criado['id'],
                'nome': 'Óculos', 'quantidade': 1, 'data_entrada': entrada,
                'data_retirada': retirada or ''})['sucesso'])
        self.assertEqual(itens_residentes.listar(self.r1)[0]['nome'], 'Óculos')
        self.assertIsNone(itens_residentes.listar(self.r1)[0]['data_retirada'])


if __name__ == '__main__':
    unittest.main()

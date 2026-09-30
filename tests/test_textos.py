import io
import json
import unittest
from unittest.mock import Mock
from src.interface.servidor import Requisicao


class Textos(unittest.TestCase):
    def ler(self, rota, dados):
        body = json.dumps(dados).encode()
        request = object.__new__(Requisicao)
        request.path = rota
        request.headers = {'Content-Length': str(len(body)), 'Content-Type': 'application/json'}
        request.connection = Mock()
        request.rfile = io.BytesIO(body)
        return request._corpo_json()

    def test_textos_e_campos_tecnicos(self):
        data = {'nome': 'João', 'observacao': 'ação de revisão', 'senha': 'AbcSenha',
                'email': 'Nome@Email.com', 'assinatura': 'aBc123', 'valor': '10.50',
                'destino': 'recebimento', 'id': 7}
        result = self.ler('/api/residentes', data)
        self.assertEqual(result, {**data, 'nome': 'JOÃO', 'observacao': 'AÇÃO DE REVISÃO'})

    def test_configuracao_e_sincronizacao_preservadas(self):
        data = {'nome': 'Abc', 'config': {'backup_directory': 'C:/MinhaPasta'}, 'senha': 'SenhaAbc'}
        for route in ['/api/backup/config', '/api/sincronizacao/importar']:
            self.assertEqual(self.ler(route, data), data)

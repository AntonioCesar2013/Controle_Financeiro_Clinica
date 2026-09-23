import unittest, uuid
from unittest.mock import patch
import test_regressoes as base
from src.financeiro import despesas
from src.interface.servidor import Requisicao


class ItensAdministracaoApi(unittest.TestCase):
    def setUp(self):
        self.f=base.Regressoes();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.sid=despesas.cadastrar_setor('Administração')['id']
    def post(self,rota,dados,chave):
        req=object.__new__(Requisicao);req.path=rota;req._corpo_json=lambda:dados
        req.headers={'Idempotency-Key':chave};req.client_address=('127.0.0.1',0);req.command='POST';req._sessao=lambda:None
        req._json=lambda payload,status=200,cookie=None:(payload,int(status),cookie) if req._capturando else ({**payload,'sucesso':False} if status>=400 else payload)
        with patch('src.interface.servidor.somente_leitura',return_value=False):return req.do_POST()
    def cadastro(self): return {'nome':'Mesa','quantidade_inicial':2,'unidade_medida':'UN','setor_id':self.sid,
        'estado_conservacao':'BOM','data_movimentacao':self.f.hoje,'motivo':'Cadastro inicial','valor_aquisicao':'0'}
    def test_reenvio_conflito_e_versao(self):
        chave=uuid.uuid4().hex; dados=self.cadastro()
        a=self.post('/api/administracao/itens',dados,chave);b=self.post('/api/administracao/itens',dados,chave)
        self.assertEqual((a['id'],a['operacao_id']),(b['id'],b['operacao_id']))
        self.assertEqual(self.f.sql('SELECT COUNT(*) FROM itens_administracao'),[(1,)])
        self.assertEqual(self.f.sql('SELECT COUNT(*) FROM movimentacoes_itens_administracao'),[(1,)])
        conflito=self.post('/api/administracao/itens',{**dados,'nome':'Outra'},chave);self.assertFalse(conflito['sucesso'])
        mov={'id':a['id'],'versao_esperada':1,'tipo':'SAIDA','quantidade':1,'data_movimentacao':self.f.hoje,'motivo':'Uso'}
        ok=self.post('/api/administracao/itens/movimentar',mov,uuid.uuid4().hex);self.assertTrue(ok['sucesso'])
        obsoleto=self.post('/api/administracao/itens/movimentar',mov,uuid.uuid4().hex)
        self.assertFalse(obsoleto['sucesso']);self.assertEqual(self.f.sql('SELECT quantidade FROM itens_administracao'),[(1,)])

    def test_valor_aquisicao_aceita_contrato_monetario_sem_conversao_dupla(self):
        casos=[(10.5,1050),('10.50',1050),(0,0)]
        for indice,(valor,esperado) in enumerate(casos):
            with self.subTest(valor=valor):
                dados={**self.cadastro(),'nome':f'Item {indice}','valor_aquisicao':valor}
                resultado=self.post('/api/administracao/itens',dados,uuid.uuid4().hex)
                self.assertTrue(resultado['sucesso'])
                self.assertEqual(self.f.sql('SELECT valor_aquisicao FROM itens_administracao WHERE id=?',(resultado['id'],)),[(esperado,)])
        ausente=self.cadastro();ausente['nome']='Sem valor';ausente.pop('valor_aquisicao')
        resultado=self.post('/api/administracao/itens',ausente,uuid.uuid4().hex)
        self.assertTrue(resultado['sucesso'])
        self.assertEqual(self.f.sql('SELECT valor_aquisicao FROM itens_administracao WHERE id=?',(resultado['id'],)),[(None,)])
        for indice,valor in enumerate((-1,'inválido',True,float('nan'))):
            with self.subTest(invalido=repr(valor)):
                dados={**self.cadastro(),'nome':f'Inválido {indice}','valor_aquisicao':valor}
                resultado=self.post('/api/administracao/itens',dados,uuid.uuid4().hex)
                self.assertFalse(resultado['sucesso'])
        self.assertEqual(self.f.sql("SELECT COUNT(*) FROM itens_administracao WHERE nome LIKE 'Inválido %'"),[(0,)])

if __name__=='__main__':unittest.main()

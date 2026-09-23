import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import test_regressoes as base
from src.administracao import itens
from src.financeiro import despesas
from src.infraestrutura import banco


class ItensAdministracao(unittest.TestCase):
    def setUp(self):
        self.f=base.Regressoes(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.s1=despesas.cadastrar_setor('Administração')['id']; self.s2=despesas.cadastrar_setor('Manutenção')['id']
        self.hoje=date.today().isoformat()
    def novo(self,**kw):
        dados=dict(nome='Notebook',descricao=None,categoria='TI',codigo_patrimonio=None,quantidade_inicial=3,
            unidade_medida='UN',setor_id=self.s1,data_aquisicao=None,valor_aquisicao=None,
            estado_conservacao='BOM',localizacao='Sala',data_movimentacao=self.hoje,motivo='Cadastro inicial')
        dados.update(kw); return itens.cadastrar(**dados)

    def test_schema_idempotente_e_isolado(self):
        self.novo(); banco.criar_tabelas(); banco.criar_tabelas()
        self.assertEqual(self.f.sql("SELECT COUNT(*) FROM migracoes_schema WHERE modulo='administracao'"),[(1,)])
        self.assertEqual(self.f.sql('SELECT COUNT(*) FROM itens_administracao'),[(1,)])
        self.assertEqual(self.f.sql('SELECT COUNT(*) FROM movimentacoes_itens_administracao'),[(1,)])
        self.assertEqual(self.f.sql('SELECT COUNT(*) FROM itens_cantina'),[(0,)])
        self.assertEqual(self.f.sql('SELECT COUNT(*) FROM itens_residentes'),[(0,)])

    def test_patrimonio_normalizacao_unicidade_e_validacoes(self):
        a=self.novo(codigo_patrimonio=' pat-01 ',quantidade_inicial=1,valor_aquisicao=0)
        self.assertEqual(itens.detalhe(a['id'])['codigo_patrimonio'],'PAT-01')
        with self.assertRaisesRegex(ValueError,'já cadastrado'): self.novo(codigo_patrimonio='PAT-01',quantidade_inicial=1)
        with self.assertRaisesRegex(ValueError,'exatamente'): self.novo(codigo_patrimonio='P2',quantidade_inicial=2)
        self.novo(nome='Notebook'); self.novo(nome='Notebook')
        futuro=(date.today()+timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError): self.novo(data_movimentacao=futuro)
        with self.assertRaises(ValueError): self.novo(valor_aquisicao=0.5)

    def test_movimentos_transferencia_status_e_snapshots(self):
        iid=self.novo()['id']; v=1
        r=itens.movimentar(iid,v,'SAIDA',self.hoje,'Uso',quantidade=1); v=r['versao']; self.assertEqual(r['quantidade'],2)
        r=itens.movimentar(iid,v,'AJUSTE',self.hoje,'Contagem',quantidade_alvo=1); v=r['versao']
        r=itens.transferir(iid,v,self.s2,'Almoxarifado',self.hoje,'Mudança'); v=r['versao']
        self.f.sql("UPDATE setores SET nome='Oficina' WHERE id=?",(self.s2,))
        hist=itens.historico(iid)['linhas']; self.assertEqual(hist[-1]['setor_novo_nome'],'Manutenção')
        r=itens.movimentar(iid,v,'SAIDA',self.hoje,'Uso final',quantidade=1); v=r['versao']
        self.assertEqual((r['quantidade'],r['ativo']),(0,1))
        r=itens.alterar_status(iid,v,0,'Sem saldo'); v=r['versao']
        with self.assertRaises(ValueError): itens.movimentar(iid,v,'ENTRADA',self.hoje,'Entrada',quantidade=1)
        r=itens.alterar_status(iid,v,1,'Retorno'); self.assertEqual(r['ativo'],1)

    def test_saldos_resultantes_de_todos_os_tipos_de_movimento(self):
        iid=self.novo(quantidade_inicial=3)['id']; versao=1
        casos=[('ENTRADA',{'quantidade':2},5,1),('SAIDA',{'quantidade':1},4,1),
               ('AJUSTE',{'quantidade_alvo':2},2,1),('BAIXA',{'quantidade':2},0,0)]
        for tipo,argumentos,saldo,ativo in casos:
            resultado=itens.movimentar(iid,versao,tipo,self.hoje,tipo,**argumentos)
            versao=resultado['versao']
            self.assertEqual((resultado['quantidade'],resultado['ativo']),(saldo,ativo))
        self.assertEqual([r['tipo'] for r in itens.historico(iid)['linhas']],
                         ['CADASTRO','ENTRADA','SAIDA','AJUSTE','BAIXA'])

    def test_setor_inativo_esvaziamento_e_concorrencia(self):
        iid=self.novo(quantidade_inicial=2)['id']; despesas.desativar_setor(self.s1)
        with self.assertRaises(ValueError): itens.movimentar(iid,1,'ENTRADA',self.hoje,'Não',quantidade=1)
        self.assertEqual(itens.movimentar(iid,1,'SAIDA',self.hoje,'Esvaziar',quantidade=1)['quantidade'],1)
        transferido=itens.transferir(iid,2,self.s2,'Destino',self.hoje,'Retirar do setor inativo')
        self.assertEqual(itens.detalhe(iid)['setor_id'],self.s2)
        self.assertEqual(transferido['versao'],3)
        iid2=self.novo(setor_id=self.s2,quantidade_inicial=1)['id']
        def sair():
            try:return itens.movimentar(iid2,1,'SAIDA',self.hoje,'Concorrente',quantidade=1)
            except Exception as e:return e
        resultados=list(ThreadPoolExecutor(max_workers=2).map(lambda _:sair(),range(2)))
        self.assertEqual(sum(isinstance(x,dict) for x in resultados),1)
        self.assertEqual(itens.detalhe(iid2)['quantidade'],0)
        self.assertEqual(len(itens.historico(iid2)['linhas']),2)

    def test_listagem_filtros_indicadores_e_unidades(self):
        self.novo(nome='Caixa',quantidade_inicial=3,unidade_medida='CX',estado_conservacao='RUIM')
        self.novo(nome='Caneta',quantidade_inicial=20,unidade_medida='UN',estado_conservacao='INSERVIVEL')
        r=itens.listar(busca='caixa',pagina=1,tamanho=1)
        self.assertEqual((r['total_geral'],r['total_filtrado'],r['indicadores']['ruim']),(2,1,1))
        geral=itens.listar(); self.assertEqual(geral['indicadores']['quantidades'],{'CX':3,'UN':20})
        with self.assertRaises(ValueError): itens.listar(ordem='DROP TABLE')

    def test_falha_no_historico_desfaz_mutacao(self):
        iid=self.novo()['id']
        self.f.sql("""CREATE TRIGGER falhar_historico BEFORE INSERT ON movimentacoes_itens_administracao
                      BEGIN SELECT RAISE(ABORT,'falha simulada'); END""")
        with self.assertRaisesRegex(Exception,'falha simulada'):
            itens.movimentar(iid,1,'SAIDA',self.hoje,'Teste',quantidade=1)
        self.assertEqual((itens.detalhe(iid)['quantidade'],itens.detalhe(iid)['versao']),(3,1))
        self.assertEqual(len(itens.historico(iid)['linhas']),1)

if __name__=='__main__': unittest.main()

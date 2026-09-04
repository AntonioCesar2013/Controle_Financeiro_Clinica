"""Regressões financeiras em bancos descartáveis, sem acessar dados da clínica."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from src.infraestrutura import banco
from src.cadastros import internacoes
from src.cantina import vendas, produtos
from src.financeiro import cobrancas, recebimentos, pagamentos, contas_receber, contas_pagar, caixa
from src.financeiro.estornos import historico
from src.interface import relatorios


class Regressoes(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory(prefix="regressao_clinica_")
        self.addCleanup(self.pasta.cleanup)
        caminho = Path(self.pasta.name) / "teste.db"
        for alvo in [banco, produtos]:
            p = patch.object(alvo, "CAMINHO_BANCO", caminho)
            p.start()
            self.addCleanup(p.stop)
        banco.criar_tabelas()
        self.hoje = date.today().isoformat()
        self.sql("INSERT INTO responsaveis(nome,cpf) VALUES('Responsavel teste','00000000001')")
        self.sql("INSERT INTO convenios(nome,valor_diaria) VALUES('Convenio teste',10000)")

    def sql(self, consulta, args=()):
        with closing(banco.conectar()) as conn, conn:
            cur = conn.execute(consulta, args)
            return cur.fetchall() if cur.description else cur.lastrowid

    def internar(self, inicio=None, modalidade="PARTICULAR", contrato=70000, acolhimento=10000, mensalidade=30000):
        rid = self.sql("INSERT INTO residentes(nome,cpf) VALUES('Teste',?)", (str(self.sql("SELECT COUNT(*) FROM residentes")[0][0]),))
        r = internacoes.cadastrar_internacao_com_cobrancas(rid, 1, inicio or self.hoje, 2, contrato, acolhimento, mensalidade, modalidade, 1)
        self.assertTrue(r["sucesso"], r)
        return rid, r["id"]

    def carteira(self):
        rid, _ = self.internar()
        wid = vendas.criar_carteira(rid, 10)["id"]
        pid = self.sql("INSERT INTO itens(nome,ativo,estoque_atual) VALUES('Teste',1,20)")
        self.sql("INSERT INTO itens_valores(item_id,valor,data_inicio_valor) VALUES(?,15,?)", (pid, self.hoje))
        return wid, pid

    def test_venda_negativa_permitida_e_estorno(self):
        wid, pid = self.carteira()
        compra = vendas.registrar_compra(wid, [{"item_id": pid, "quantidade": 1}])
        self.assertTrue(compra["sucesso"])
        self.assertEqual(compra["saldo"], -5)
        self.assertEqual(vendas.estornar_compra(compra["id"])["saldo"], 10)
        self.assertFalse(vendas.estornar_compra(compra["id"])["sucesso"])
        self.assertEqual(self.sql("SELECT estoque_atual FROM itens")[0][0], 20)
        self.assertEqual(vendas.registrar_venda(wid, pid)["saldo"], -5)

    def test_corrigir_credito_consumido_inclusive_carteira_negativa(self):
        wid, pid = self.carteira()
        vendas.adicionar_credito(wid, 100)
        mid = self.sql("SELECT MAX(id) FROM movimentacoes_carteira")[0][0]
        vendas.registrar_compra(wid, [{"item_id": pid, "quantidade": 4}])
        r = vendas.corrigir_credito(mid, 120)
        self.assertTrue(r["sucesso"])
        self.assertEqual(r["saldo"], 70)
        self.assertEqual(vendas.corrigir_credito(r["id"], 20)["saldo"], -30)

    def test_datas_invalidas_nao_sao_gravadas(self):
        _, iid = self.internar()
        cid = self.sql("SELECT id FROM cobrancas WHERE internacao_id=?", (iid,))[0][0]
        for data in [None, "", "2026-02-30", "20260903", "2026-9-3"]:
            self.assertFalse(recebimentos.registrar_pagamento(cid, data, 10000)["sucesso"])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM recebimentos")[0][0], 0)
        self.assertEqual(len(contas_receber.listar_cobrancas_consolidadas()), 3)

    def test_encerramento_futuro_recusado(self):
        rid, iid = self.internar()
        self.assertFalse(internacoes.encerrar_internacao(iid, (date.today()+timedelta(days=10)).isoformat())["sucesso"])
        self.assertEqual(self.sql("SELECT ativo FROM residentes WHERE id=?", (rid,))[0][0], 1)
        self.assertIsNone(self.sql("SELECT encerrada_em FROM internacoes")[0][0])

    def convenio(self):
        _, iid = self.internar("2026-08-01", "CONVENIO")
        cid = self.sql("SELECT id FROM cobrancas WHERE internacao_id=? ORDER BY id", (iid,))[0][0]
        return iid, cid

    def test_desconto_convenio_exige_autorizacao_e_preserva_historico(self):
        iid, cid = self.convenio()
        self.assertTrue(cobrancas.aplicar_desconto(cid, 200000)["sucesso"])
        self.assertFalse(internacoes.encerrar_internacao(iid, "2026-08-10")["sucesso"])
        self.assertEqual(self.sql("SELECT valor,desconto FROM cobrancas WHERE id=?", (cid,))[0], (310000, 200000))
        self.assertIsNone(self.sql("SELECT encerrada_em FROM internacoes")[0][0])
        self.assertTrue(internacoes.encerrar_internacao(iid, "2026-08-10", autorizar_ajuste_desconto=True)["sucesso"])
        self.assertEqual(self.sql("SELECT valor,desconto,status FROM cobrancas WHERE id=?", (cid,))[0], (100000, 100000, "DESCONTADA"))
        self.assertEqual(self.sql("SELECT desconto_anterior,desconto_novo FROM ajustes_cobrancas WHERE cobranca_id=?", (cid,))[0], (200000, 100000))

    def test_convenio_parcial_recalculado_e_excesso_bloqueado(self):
        iid, cid = self.convenio()
        r = recebimentos.registrar_pagamento(cid, "2026-08-05", 120000)
        self.assertTrue(r["sucesso"])
        self.assertFalse(internacoes.encerrar_internacao(iid, "2026-08-10", autorizar_ajuste_desconto=True)["sucesso"])
        self.assertIsNone(self.sql("SELECT encerrada_em FROM internacoes")[0][0])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM ajustes_cobrancas")[0][0], 0)
        self.assertTrue(recebimentos.excluir_recebimento(r["id"], "Acerto")["sucesso"])
        recebimentos.registrar_pagamento(cid, "2026-08-05", 50000)
        self.assertTrue(internacoes.encerrar_internacao(iid, "2026-08-10")["sucesso"])
        self.assertEqual(self.sql("SELECT valor,status FROM cobrancas WHERE id=?", (cid,))[0], (100000, "PARCIAL"))

    def test_preco_futuro_nao_aparece_no_relatorio(self):
        _, pid = self.carteira()
        self.sql("INSERT INTO itens_valores(item_id,valor,data_inicio_valor) VALUES(?,99,?)", (pid, (date.today()+timedelta(days=30)).isoformat()))
        self.assertEqual(relatorios.gerar("estoque")["linhas"][0]["valor_atual"], 15)

    def conta(self, status="ABERTA"):
        sid = self.sql("INSERT INTO setores(nome) VALUES('Teste')")
        did = self.sql("INSERT INTO despesas(setor_id,descricao,natureza) VALUES(?,'Teste','FIXA')", (sid,))
        return self.sql("INSERT INTO contas_pagar(despesa_id,data_vencimento,valor,status) VALUES(?,'2026-08-10',10000,?)", (did, status))

    def test_relatorio_respeita_cancelamento_e_data_de_pagamento(self):
        cp = self.conta("CANCELADA")
        def rel(mes):
            return relatorios.gerar("despesas_setor", f"2026-{mes}-01", f"2026-{mes}-30")["linhas"][0]
        self.assertEqual(rel("08")["total_previsto"], 0)
        self.sql("UPDATE contas_pagar SET status='ABERTA' WHERE id=?", (cp,))
        self.assertTrue(pagamentos.registrar_pagamento(cp, "2026-09-03", 10000)["sucesso"])
        self.assertEqual(rel("08")["total_pago"], 0)
        self.assertEqual(rel("09")["total_pago"], 10000)
        self.assertEqual(rel("09")["total_previsto"], 0)

    def test_pagamento_com_desconto_atualiza_conta_na_mesma_operacao(self):
        conta_id = self.conta()
        resultado = pagamentos.registrar_pagamento(
            conta_id, self.hoje, 3000, "PIX", valor_desconto=2000,
        )
        self.assertTrue(resultado["sucesso"], resultado)
        self.assertEqual(resultado["restante"], 5000)
        self.assertEqual(caixa.resumo_caixa()["total_saidas"], 3000)
        self.assertEqual(
            self.sql("SELECT desconto,status FROM contas_pagar WHERE id=?", (conta_id,))[0],
            (2000, "PARCIAL"),
        )
        consolidada = next(item for item in contas_pagar.listar_contas() if item["id"] == conta_id)
        self.assertEqual((consolidada["total_pago"], consolidada["restante"]), (3000, 5000))

    def test_estornos_preservam_lancamentos_e_recalculam_caixa(self):
        _, iid = self.internar()
        cid = self.sql("SELECT id FROM cobrancas WHERE internacao_id=?", (iid,))[0][0]
        r = recebimentos.registrar_pagamento(cid, self.hoje, 10000, "DINHEIRO", "Original")
        self.assertEqual(caixa.resumo_caixa()["total_entradas"], 10000)
        self.assertTrue(recebimentos.excluir_recebimento(r["id"], "Duplicado")["sucesso"])
        self.assertFalse(recebimentos.excluir_recebimento(r["id"])["sucesso"])
        h = historico("recebimentos", cid, recebimentos.buscar_pagamentos(cid))
        self.assertTrue(h[0]["estornada"])
        self.assertEqual(h[0]["observacao"], "Original")
        self.assertEqual(h[0]["motivo_estorno"], "Duplicado")
        self.assertEqual(caixa.resumo_caixa()["total_entradas"], 0)
        cp = self.conta()
        p = pagamentos.registrar_pagamento(cp, self.hoje, 10000)
        self.assertTrue(pagamentos.excluir_pagamento(p["id"], "Duplicado")["sucesso"])
        self.assertTrue(historico("pagamentos_saida", cp, [])[0]["estornada"])
        self.assertEqual(caixa.resumo_caixa()["total_saidas"], 0)
        self.assertEqual(self.sql("SELECT status FROM contas_pagar")[0][0], "ABERTA")

    def test_contrato_incoerente_recusado_e_zero_resolvido(self):
        rid = self.sql("INSERT INTO residentes(nome,cpf) VALUES('Teste','123')")
        self.assertFalse(internacoes.cadastrar_internacao_com_cobrancas(rid, 1, self.hoje, 2, 100000, 10000, 30000)["sucesso"])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM internacoes")[0][0], 0)
        self.internar(contrato=0, acolhimento=0, mensalidade=0)
        self.assertTrue(all(r[0] == "DESCONTADA" for r in self.sql("SELECT status FROM cobrancas")))

    def test_cancelar_agendamento_libera_periodo_e_preserva_cobrancas(self):
        futuro = (date.today()+timedelta(days=10)).isoformat()
        rid, iid = self.internar(futuro)
        self.assertTrue(internacoes.cancelar_agendamento(iid)["sucesso"])
        internacoes.sincronizar_status_residentes(futuro)
        self.assertEqual(self.sql("SELECT status FROM internacoes")[0][0], "CANCELADA")
        self.assertEqual(self.sql("SELECT SUM(valor-desconto) FROM cobrancas")[0][0], 0)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM ajustes_cobrancas")[0][0], 3)
        self.assertTrue(internacoes.cadastrar_internacao_com_cobrancas(rid, 1, futuro, 2, 70000, 10000, 30000)["sucesso"])

    def test_migracao_repetivel_preserva_dados(self):
        self.internar()
        banco.criar_tabelas()
        banco.criar_tabelas()
        self.assertEqual(self.sql("SELECT COUNT(*) FROM internacoes")[0][0], 1)
        self.assertEqual(self.sql("PRAGMA integrity_check")[0][0], "ok")

    def test_recebimentos_concorrentes_nao_ultrapassam_cobranca(self):
        _, iid = self.internar()
        cid = self.sql("SELECT id FROM cobrancas WHERE internacao_id=?", (iid,))[0][0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(lambda _: recebimentos.registrar_pagamento(cid, self.hoje, 10000), range(2)))
        self.assertEqual(sum(r["sucesso"] for r in resultados), 1)
        self.assertEqual(self.sql("SELECT SUM(valor) FROM recebimentos")[0][0], 10000)

    def test_recebimento_com_desconto_atualiza_cobranca_na_mesma_operacao(self):
        _, iid = self.internar()
        cid = self.sql(
            "SELECT id FROM cobrancas WHERE internacao_id=? AND tipo='MENSALIDADE' ORDER BY id",
            (iid,),
        )[0][0]
        resultado = recebimentos.registrar_pagamento(
            cid, self.hoje, 10000, "PIX", valor_desconto=5000,
        )
        self.assertTrue(resultado["sucesso"], resultado)
        self.assertEqual(resultado["restante"], 15000)
        self.assertEqual(
            self.sql("SELECT desconto,status FROM cobrancas WHERE id=?", (cid,))[0],
            (5000, "PARCIAL"),
        )
        recusado = recebimentos.registrar_pagamento(
            cid, self.hoje, 15001, "PIX", valor_desconto=0,
        )
        self.assertFalse(recusado["sucesso"])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM recebimentos WHERE cobranca_id=?", (cid,))[0][0], 1)

    def test_rotas_de_recebimento_estorno_e_ajustes(self):
        from src.interface.servidor import Requisicao
        _, iid = self.internar()
        cid = self.sql("SELECT id FROM cobrancas WHERE internacao_id=?", (iid,))[0][0]
        requisicao = object.__new__(Requisicao)
        requisicao._json = lambda payload, *args, **kwargs: payload
        requisicao.path = "/api/recebimentos"
        requisicao._corpo_json = lambda: {"cobranca_id": cid, "data_pagamento": "2026-02-30", "valor": "100"}
        with patch("src.interface.servidor.somente_leitura", return_value=False):
            self.assertFalse(requisicao.do_POST()["sucesso"])
            requisicao._corpo_json = lambda: {"cobranca_id": cid, "data_pagamento": self.hoje, "valor": "100"}
            r = requisicao.do_POST()
            self.assertTrue(r["sucesso"])
            requisicao.path = "/api/recebimentos/excluir"
            requisicao._corpo_json = lambda: {"recebimento_id": r["id"], "motivo": "Teste de estorno"}
            self.assertTrue(requisicao.do_POST()["sucesso"])
        h = requisicao._get_api("/api/contas-receber/recebimentos", {"id": [str(cid)]})
        self.assertTrue(h["dados"][0]["estornada"])
        self.assertEqual(requisicao._get_api("/api/cobrancas/ajustes", {"id": [str(cid)]})["dados"], [])

    def test_centavos_exatos_com_dez_compras_de_dez_centavos(self):
        from src.financeiro.moeda import reais_para_centavos
        self.assertEqual(reais_para_centavos("1.234,56"), 123456)
        self.assertEqual(reais_para_centavos("0.105"), 11)
        self.assertEqual(reais_para_centavos("-0,10"), -10)
        for invalido in ["NaN", "Infinity", "abc", True]:
            with self.assertRaises(ValueError): reais_para_centavos(invalido)
        wid, pid = self.carteira()
        self.sql("UPDATE itens_valores SET valor=10")
        self.sql("UPDATE carteiras SET saldo=100")
        for _ in range(10):
            self.assertTrue(vendas.registrar_compra(wid, [{"item_id": pid, "quantidade": 1}])["sucesso"])
        self.assertEqual(self.sql("SELECT saldo,typeof(saldo) FROM carteiras")[0], (0, "integer"))

    def test_api_cantina_converte_reais_uma_unica_vez(self):
        from src.interface.servidor import Requisicao
        wid, _ = self.carteira()
        req = object.__new__(Requisicao)
        req._json = lambda payload, *args, **kwargs: payload
        req.path = "/api/carteiras/credito"
        req._corpo_json = lambda: {"carteira_id": wid, "valor": "1,25"}
        with patch("src.interface.servidor.somente_leitura", return_value=False):
            self.assertTrue(req.do_POST()["sucesso"])
            req.path = "/api/itens"
            req._corpo_json = lambda: {"nome": "Novo produto", "valor": "12.34"}
            self.assertTrue(req.do_POST()["sucesso"])
        self.assertEqual(self.sql("SELECT valor_total FROM movimentacoes_carteira ORDER BY id DESC LIMIT 1")[0][0], 125)
        self.assertEqual(self.sql("SELECT valor FROM itens_valores ORDER BY id DESC LIMIT 1")[0][0], 1234)

    def test_falha_monetaria_reverte_toda_migracao(self):
        from src.infraestrutura.migracao_centavos import migrar
        with closing(banco.conectar()) as conn:
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("DROP TABLE itens_valores")
            conn.execute("DROP TABLE carteiras")
            conn.execute("CREATE TABLE itens_valores(id INTEGER PRIMARY KEY AUTOINCREMENT,valor REAL)")
            conn.execute("CREATE TABLE carteiras(id INTEGER PRIMARY KEY AUTOINCREMENT,saldo REAL)")
            conn.execute("INSERT INTO itens_valores(valor) VALUES(12.34)")
            conn.execute("INSERT INTO carteiras(saldo) VALUES('invalido')")
            conn.commit()
            with self.assertRaises(ValueError): migrar(conn)
            self.assertEqual(conn.execute("SELECT valor FROM itens_valores").fetchone()[0], 12.34)
            self.assertEqual(conn.execute("PRAGMA table_info(itens_valores)").fetchall()[1][2], "REAL")

    def test_recibo_parcial_idempotente_preserva_dados_e_sinaliza_estorno(self):
        from src.financeiro import recibos
        _, iid = self.internar()
        cid = self.sql("SELECT id FROM cobrancas WHERE internacao_id=? AND tipo='MENSALIDADE' ORDER BY id", (iid,))[0][0]
        pagamento = recebimentos.registrar_pagamento(cid, self.hoje, 10000)
        recibo = recibos.gerar(pagamento["id"])
        self.assertEqual(recibo["dados"]["valor"], 10000)
        self.assertEqual(recibo["dados"]["valor_devido"], 30000)
        self.assertEqual(recibos.gerar(pagamento["id"])["numero"], recibo["numero"])
        self.sql("UPDATE residentes SET nome='Nome alterado'")
        self.assertEqual(recibos.consultar(recibo["id"])["dados"]["residente_nome"], "Teste")
        recebimentos.excluir_recebimento(pagamento["id"], "Teste")
        self.assertTrue(recibos.consultar(recibo["id"])["cancelado"])
        with self.assertRaises(ValueError): recibos.gerar(pagamento["id"])
        with self.assertRaises(ValueError): recibos.gerar(99999)

    def test_extrato_periodo_e_residente_isolados(self):
        from src.interface.extrato_residente import consultar
        rid, iid = self.internar()
        outro, _ = self.internar()
        cid = self.sql("SELECT id FROM cobrancas WHERE internacao_id=? AND tipo='MENSALIDADE' ORDER BY id", (iid,))[0][0]
        recebimentos.registrar_pagamento(cid, "2026-08-05", 12345)
        wid = vendas.criar_carteira(rid, 0)["id"]
        vendas.adicionar_credito(wid, 10000, "2026-08-01")
        vendas.adicionar_credito(wid, 5000, "2026-08-10")
        d = consultar(rid, "2026-08-05", "2026-08-15")
        self.assertEqual(d["resumo"]["recebido_periodo"], 12345)
        self.assertEqual(d["resumo"]["carteira_abertura"], 10000)
        self.assertEqual(d["resumo"]["carteira_fechamento"], 15000)
        self.assertEqual(len(d["movimentacoes_carteira"]), 1)
        self.assertEqual(consultar(outro)["recebimentos"], [])
        with self.assertRaises(ValueError): consultar(rid, "2026-09-01", "2026-08-01")

    def test_migracao_legada_com_backup_saldos_negativos_e_reexecucao(self):
        import re
        from src.infraestrutura.migracao_centavos import CAMPOS
        rid, _ = self.internar()
        with closing(banco.conectar()) as conn:
            conn.execute("PRAGMA foreign_keys=OFF")
            for tabela, campos in CAMPOS.items():
                esquema = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (tabela,)).fetchone()[0]
                esquema = esquema.replace(f"CREATE TABLE {tabela}", f"CREATE TABLE {tabela}_legada")
                for campo in campos:
                    esquema = re.sub(r'\b'+campo+r'\s+INTEGER', campo+' REAL', esquema)
                conn.execute(esquema)
                conn.execute(f'DROP TABLE {tabela}')
                conn.execute(f'ALTER TABLE {tabela}_legada RENAME TO {tabela}')
            conn.execute("INSERT INTO carteiras(id,residente_id,saldo) VALUES(1,?,-12.34)", (rid,))
            conn.execute("INSERT INTO itens(id,nome) VALUES(1,'Legado')")
            conn.execute("INSERT INTO itens_valores(id,item_id,valor,data_inicio_valor) VALUES(1,1,0.10,'2026-08-01')")
            conn.execute("INSERT INTO vendas_cantina(id,carteira_id,data_movimentacao,valor_total) VALUES(1,1,'2026-08-01',12.34)")
            conn.execute("INSERT INTO vendas_cantina_itens(venda_id,item_id,item_valor_id,quantidade,valor_unitario,valor_total) VALUES(1,1,1,1,12.34,12.34)")
            conn.execute("INSERT INTO movimentacoes_carteira(carteira_id,tipo,quantidade,valor_total,data_movimentacao) VALUES(1,'CREDITO',1,10.25,'2026-08-01')")
            conn.execute("INSERT INTO movimentacoes_estoque(item_id,quantidade_anterior,quantidade_movimentada,quantidade_atual,motivo,data_movimentacao,custo_unitario) VALUES(1,0,1,1,'Teste','2026-08-01',1.99)")
            conn.commit()
        banco.criar_tabelas()
        self.assertEqual(self.sql("SELECT saldo,typeof(saldo) FROM carteiras")[0], (-1234, "integer"))
        self.assertEqual(self.sql("SELECT valor FROM itens_valores")[0][0], 10)
        self.assertEqual(self.sql("SELECT valor_total FROM vendas_cantina")[0][0], 1234)
        self.assertEqual(self.sql("SELECT valor_unitario FROM vendas_cantina_itens")[0][0], 1234)
        self.assertEqual(self.sql("SELECT valor_total FROM movimentacoes_carteira")[0][0], 1025)
        self.assertEqual(self.sql("SELECT custo_unitario FROM movimentacoes_estoque")[0][0], 199)
        self.assertEqual(self.sql("PRAGMA foreign_key_check"), [])
        backups = list((banco.CAMINHO_BANCO.parent/'backups').glob('*antes_centavos.db'))
        self.assertEqual(len(backups), 1)
        banco.criar_tabelas()
        self.assertEqual(self.sql("SELECT saldo FROM carteiras")[0][0], -1234)
        self.assertEqual(len(list((banco.CAMINHO_BANCO.parent/'backups').glob('*antes_centavos.db'))), 1)

    def test_populador_ficticio_garante_seis_meses_com_volume_e_inadimplencia(self):
        from src.scripts import popular_banco

        with patch("builtins.print"):
            popular_banco.popular_banco(fazer_backup=False)
        with closing(banco.conectar()) as conn:
            linhas, inadimplencias = popular_banco._validar(conn)
            self.assertEqual(len(linhas), 6)
            self.assertTrue(all(linha[1] >= 30 for linha in linhas))
            self.assertGreaterEqual(inadimplencias, 5)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM vendas_cantina").fetchone()[0], 72)


if __name__ == "__main__":
    unittest.main()

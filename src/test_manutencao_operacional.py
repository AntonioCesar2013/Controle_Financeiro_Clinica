import tempfile
import unittest
import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src import banco, cantina, colaboradores, internacoes, itens, residentes, responsaveis


class TestManutencaoOperacional(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "manutencao.db"
        self.patches = [
            patch.object(banco, "CAMINHO_BANCO", self.db),
            patch.object(itens, "CAMINHO_BANCO", self.db),
        ]
        for patcher in self.patches:
            patcher.start()
        banco.criar_tabelas()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp.cleanup()

    def _base_operacional(self):
        residente = residentes.cadastrar_residente("Residente", "11122233344", "Cascavel")
        responsavel = responsaveis.cadastrar_responsavel("Responsável", "55566677788", None, None)
        internacao = internacoes.cadastrar_internacao(
            residente["id"], responsavel["id"], date.today().isoformat(), 3,
            300000, 50000, 100000,
        )
        return residente, responsavel, internacao

    def test_carteira_credito_correcao_estorno_e_status(self):
        residente, _, _ = self._base_operacional()
        produto = itens.cadastrar_produto("Água", 5, 10, 2, data_inicio_valor=date.today().isoformat())
        carteira = cantina.criar_carteira(residente["id"], 20)
        credito = cantina.adicionar_credito(carteira["id"], 10)
        detalhe = cantina.consultar_carteira(carteira["id"])
        movimento_credito = next(x for x in detalhe["creditos"] if x["valor_total"] == 10)
        corrigido = cantina.corrigir_credito(movimento_credito["id"], 15)
        self.assertTrue(corrigido["sucesso"])
        venda = cantina.registrar_venda(carteira["id"], produto["id"], 2)
        self.assertTrue(venda["sucesso"])
        self.assertTrue(cantina.estornar_movimentacao(venda["id"], "Compra cancelada")["sucesso"])
        detalhe = cantina.consultar_carteira(carteira["id"])
        self.assertEqual(35, detalhe["carteira"]["saldo"])
        self.assertTrue(next(x for x in detalhe["compras"] if x["id"] == venda["id"])["estornada"])
        self.assertTrue(cantina.alterar_status_carteira(carteira["id"], 0)["sucesso"])

    def test_edicoes_encerramento_produto_e_colaborador(self):
        residente, responsavel, internacao = self._base_operacional()
        outro = responsaveis.cadastrar_responsavel("Outro", "99988877766", None, None)
        self.assertTrue(residentes.editar_residente(residente["id"], "Residente Editado", "11122233344", "Toledo")["sucesso"])
        self.assertTrue(responsaveis.editar_responsavel(responsavel["id"], "Responsável Editado", "55566677788", "45999990000", "r@example.com", 1)["sucesso"])
        self.assertTrue(internacoes.alterar_responsavel_principal(internacao["id"], outro["id"])["sucesso"])
        self.assertTrue(internacoes.encerrar_internacao(internacao["id"], date.today().isoformat(), "Alta")["sucesso"])

        produto = itens.cadastrar_produto("Suco", 4, 10, 2, data_inicio_valor=date.today().isoformat())
        self.assertTrue(itens.editar_produto(produto["id"], "Suco natural", None, None, "Bebidas", "UN", 3, 1)["sucesso"])
        self.assertTrue(itens.ajustar_estoque(
            produto["id"], 5, "Reposição", tipo="ENTRADA", custo_unitario=2.25,
            fornecedor="Distribuidora Teste", documento="NF-123", lote="L01",
            data_validade="2027-01-31",
        )["sucesso"])
        self.assertTrue(itens.cadastrar_valor_item(produto["id"], 4.5, date.today().isoformat())["sucesso"])
        movimentos = itens.listar_movimentacoes_estoque(produto["id"])
        self.assertEqual(2, len(movimentos))
        self.assertEqual("ENTRADA", movimentos[0]["tipo"])
        self.assertEqual(2.25, movimentos[0]["custo_unitario"])
        self.assertEqual("Distribuidora Teste", movimentos[0]["fornecedor"])
        self.assertEqual("SALDO_INICIAL", movimentos[1]["tipo"])
        self.assertEqual(2, len(itens.listar_valores_item(produto["id"], False)))

        colaborador = colaboradores.cadastrar_colaborador("Operador", "12345678900", "senha-antiga")
        self.assertTrue(colaboradores.editar_colaborador(colaborador["id"], "Operador Editado", "12345678900", "ATIVO")["sucesso"])
        self.assertTrue(colaboradores.redefinir_senha(colaborador["id"], "senha-nova")["sucesso"])
        self.assertIsNotNone(colaboradores.autenticar_colaborador("12345678900", "senha-nova"))

    def test_caixa_codigo_barras_carrinho_e_estorno_do_cupom(self):
        residente, _, _ = self._base_operacional()
        hoje = date.today().isoformat()
        agua = itens.cadastrar_produto(
            "Água", 5, 10, 2, codigo_barras="7890000000001",
            data_inicio_valor=hoje,
        )
        suco = itens.cadastrar_produto(
            "Suco", 7, 8, 2, codigo_barras="7890000000002",
            data_inicio_valor=hoje,
        )
        servico = itens.cadastrar_produto(
            "Corte de cabelo", 30, 0, 0, categoria="Serviços",
            data_inicio_valor=hoje,
        )
        carteira = cantina.criar_carteira(residente["id"], 100)

        produto_lido = cantina.buscar_produto_codigo("7890000000001", hoje)
        self.assertTrue(produto_lido["sucesso"])
        self.assertEqual(agua["id"], produto_lido["id"])
        self.assertFalse(cantina.buscar_produto_codigo("0000000000000", hoje)["sucesso"])

        compra_sem_saldo = cantina.registrar_compra(carteira["id"], [
            {"item_id": agua["id"], "quantidade": 10},
            {"item_id": suco["id"], "quantidade": 8},
        ], hoje)
        self.assertTrue(compra_sem_saldo["sucesso"])
        self.assertEqual(-6, compra_sem_saldo["saldo"])
        self.assertTrue(cantina.estornar_compra(compra_sem_saldo["id"], "Preparar continuação do teste")["sucesso"])

        compra_servico = cantina.registrar_compra(carteira["id"], [
            {"item_id": servico["id"], "quantidade": 1},
        ], hoje)
        self.assertTrue(compra_servico["sucesso"])
        self.assertEqual(70, compra_servico["saldo"])
        self.assertEqual(0, len(itens.listar_movimentacoes_estoque(servico["id"])))
        self.assertTrue(cantina.estornar_compra(compra_servico["id"], "Serviço cancelado")["sucesso"])

        compra = cantina.registrar_compra(carteira["id"], [
            {"item_id": agua["id"], "quantidade": 1},
            {"item_id": agua["id"], "quantidade": 2},
            {"item_id": suco["id"], "quantidade": 2},
        ], hoje)
        self.assertTrue(compra["sucesso"])
        self.assertEqual(29, compra["valor_total"])
        self.assertEqual(5, compra["quantidade_itens"])
        self.assertEqual(71, compra["saldo"])

        conn = banco.conectar()
        conn.row_factory = sqlite3.Row
        try:
            linhas = conn.execute(
                "SELECT item_id,quantidade FROM vendas_cantina_itens WHERE venda_id=? ORDER BY item_id",
                (compra["id"],),
            ).fetchall()
            movimentos = conn.execute(
                "SELECT venda_id,estornada FROM movimentacoes_carteira WHERE venda_id=?",
                (compra["id"],),
            ).fetchall()
            estoques = dict(conn.execute("SELECT id,estoque_atual FROM itens"))
        finally:
            conn.close()
        self.assertEqual([(agua["id"], 3), (suco["id"], 2)], [(x["item_id"], x["quantidade"]) for x in linhas])
        self.assertEqual(2, len(movimentos))
        self.assertEqual(7, estoques[agua["id"]])
        self.assertEqual(6, estoques[suco["id"]])

        bloqueado = cantina.estornar_movimentacao(compra["movimentacoes"][0], "Estorno indevido")
        self.assertFalse(bloqueado["sucesso"])
        estorno = cantina.estornar_compra(compra["id"], "Cancelamento do cupom")
        self.assertTrue(estorno["sucesso"])
        self.assertEqual(100, estorno["saldo"])
        self.assertFalse(cantina.estornar_compra(compra["id"])["sucesso"])

        conn = banco.conectar()
        try:
            estoques = dict(conn.execute("SELECT id,estoque_atual FROM itens"))
            status = conn.execute("SELECT status FROM vendas_cantina WHERE id=?", (compra["id"],)).fetchone()[0]
            estornadas = conn.execute(
                "SELECT COUNT(*) FROM movimentacoes_carteira WHERE venda_id=? AND estornada=1", (compra["id"],)
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(10, estoques[agua["id"]])
        self.assertEqual(8, estoques[suco["id"]])
        self.assertEqual("ESTORNADA", status)
        self.assertEqual(2, estornadas)
        tipos_agua = [x["tipo"] for x in itens.listar_movimentacoes_estoque(agua["id"])]
        self.assertEqual(["ESTORNO", "VENDA", "ESTORNO", "VENDA", "SALDO_INICIAL"], tipos_agua)

    def test_saida_manual_nao_permite_estoque_negativo(self):
        produto = itens.cadastrar_produto(
            "Barra de cereal", 4, 3, 1, codigo_barras="7890000000003",
            data_inicio_valor=date.today().isoformat(),
        )
        saida = itens.ajustar_estoque(
            produto["id"], 2, "Perda por avaria", tipo="SAIDA",
            data_movimentacao=date.today().isoformat(),
        )
        self.assertTrue(saida["sucesso"])
        self.assertEqual(1, saida["estoque_atual"])
        invalida = itens.ajustar_estoque(produto["id"], 2, "Nova perda", tipo="SAIDA")
        self.assertFalse(invalida["sucesso"])
        self.assertIn("estoque negativo", invalida["erro"])


if __name__ == "__main__":
    unittest.main()

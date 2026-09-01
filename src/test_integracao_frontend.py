import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from src import banco
from src import colaboradores
from src import consultas_interface
from src import itens
from src import recebimentos
from src.servidor import Requisicao, SESSOES


class TestIntegracaoFrontend(unittest.TestCase):
    def setUp(self):
        self.diretorio = tempfile.TemporaryDirectory()
        self.caminho_banco = Path(self.diretorio.name) / "clinica.db"
        self.patch_caminho = patch.object(banco, "CAMINHO_BANCO", self.caminho_banco)
        self.patch_caminho.start()
        self.patch_itens = patch.object(itens, "CAMINHO_BANCO", self.caminho_banco)
        self.patch_itens.start()
        self.patch_recebimentos = patch.object(recebimentos, "CAMINHO_BANCO", self.caminho_banco)
        self.patch_recebimentos.start()
        banco.criar_tabelas()

    def tearDown(self):
        SESSOES.clear()
        self.patch_recebimentos.stop()
        self.patch_itens.stop()
        self.patch_caminho.stop()
        self.diretorio.cleanup()

    def test_primeiro_acesso_e_autenticacao(self):
        self.assertFalse(colaboradores.possui_colaboradores())

        resultado = colaboradores.cadastrar_colaborador(
            "Administrador",
            "123.456.789-00",
            "senha-segura",
        )

        self.assertTrue(resultado["sucesso"])
        self.assertTrue(colaboradores.possui_colaboradores())
        self.assertIsNotNone(
            colaboradores.autenticar_colaborador("12345678900", "senha-segura")
        )
        self.assertIsNone(
            colaboradores.autenticar_colaborador("12345678900", "senha-incorreta")
        )

    def test_consultas_retornam_dados_reais_do_banco(self):
        conexao = banco.conectar()
        try:
            conexao.execute(
                "INSERT INTO residentes (nome, cpf, cidade_origem) VALUES (?, ?, ?)",
                ("Residente Real", "11122233344", "Campinas"),
            )
            conexao.commit()
        finally:
            conexao.close()

        residentes = consultas_interface.listar_residentes()

        self.assertEqual(1, len(residentes))
        self.assertEqual("Residente Real", residentes[0]["nome"])
        self.assertEqual("11122233344", residentes[0]["cpf"])

    def test_fluxo_http_de_primeiro_acesso_login_e_consulta(self):
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), Requisicao)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        conexao = http.client.HTTPConnection("127.0.0.1", servidor.server_port)

        try:
            conexao.request("GET", "/api/auth/status")
            resposta = conexao.getresponse()
            status = json.loads(resposta.read())
            self.assertFalse(status["configurado"])

            corpo = json.dumps({
                "nome": "Administrador",
                "cpf": "12345678900",
                "senha": "senha-segura",
            })
            conexao.request(
                "POST",
                "/api/auth/setup",
                body=corpo,
                headers={"Content-Type": "application/json"},
            )
            resposta = conexao.getresponse()
            resposta.read()
            self.assertEqual(201, resposta.status)

            conexao.request(
                "POST",
                "/api/auth/login",
                body=json.dumps({"cpf": "12345678900", "senha": "senha-segura"}),
                headers={"Content-Type": "application/json"},
            )
            resposta = conexao.getresponse()
            resposta.read()
            cookie = resposta.getheader("Set-Cookie").split(";", 1)[0]
            self.assertEqual(200, resposta.status)

            conexao.request("GET", "/api/residentes", headers={"Cookie": cookie})
            resposta = conexao.getresponse()
            payload = json.loads(resposta.read())
            self.assertEqual(200, resposta.status)
            self.assertEqual([], payload["dados"])

            conexao.request(
                "POST",
                "/api/colaboradores",
                body=json.dumps({
                    "nome": "Colaborador Operacional",
                    "cpf": "98765432100",
                    "senha": "outra-senha-segura",
                    "status": "ATIVO",
                }),
                headers={"Content-Type": "application/json", "Cookie": cookie},
            )
            resposta = conexao.getresponse()
            resposta.read()
            self.assertEqual(201, resposta.status)

            conexao.request("GET", "/api/colaboradores", headers={"Cookie": cookie})
            resposta = conexao.getresponse()
            payload = json.loads(resposta.read())
            self.assertEqual(200, resposta.status)
            self.assertEqual(2, len(payload["dados"]))
            self.assertNotIn("senha_hash", payload["dados"][0])
        finally:
            conexao.close()
            servidor.shutdown()
            servidor.server_close()
            thread.join(timeout=2)

    def test_rotas_permanecem_abertas_durante_fase_de_testes(self):
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), Requisicao)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        conexao = http.client.HTTPConnection("127.0.0.1", servidor.server_port)

        try:
            conexao.request("GET", "/api/residentes")
            resposta = conexao.getresponse()
            payload = json.loads(resposta.read())
            self.assertEqual(200, resposta.status)
            self.assertEqual([], payload["dados"])
        finally:
            conexao.close()
            servidor.shutdown()
            servidor.server_close()
            thread.join(timeout=2)

    def test_todas_as_rotas_de_cadastro(self):
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), Requisicao)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        conexao = http.client.HTTPConnection("127.0.0.1", servidor.server_port)

        def post(rota, dados, esperado=201):
            conexao.request("POST", rota, body=json.dumps(dados), headers={"Content-Type": "application/json"})
            resposta = conexao.getresponse()
            payload = json.loads(resposta.read())
            self.assertEqual(esperado, resposta.status, (rota, payload))
            self.assertTrue(payload.get("sucesso"), (rota, payload))
            return payload

        try:
            residente = post("/api/residentes", {
                "nome": "Residente Cadastro", "cpf": "11122233344", "cidade_origem": "Jesuítas",
            })
            responsavel = post("/api/responsaveis", {
                "nome": "Responsável Cadastro", "cpf": "55566677788",
                "telefone": "45999990000", "email": "responsavel@example.com",
            })
            internacao = post("/api/internacoes", {
                "residente_id": residente["id"], "responsavel_id": responsavel["id"],
                "data_acolhimento": "2026-08-28", "periodo_tratamento": 3,
                "valor_contrato": 3000, "valor_acolhimento": 500, "valor_mensalidade": 1000,
            })
            self.assertEqual(4, internacao["cobrancas"])
            conexao.request("GET", "/api/mensalidades")
            resposta = conexao.getresponse(); mensalidades = json.loads(resposta.read())["dados"]
            self.assertEqual(200, resposta.status)
            self.assertEqual(3, len(mensalidades))
            self.assertEqual("Residente Cadastro", mensalidades[0]["residente_nome"])
            setor = post("/api/setores", {"nome": "Administrativo"})
            tipo = post("/api/tipos-despesa", {"nome": "Serviços"})
            post("/api/setores/editar", {"id": setor["id"], "nome": "Administração", "ativo": 1}, esperado=200)
            post("/api/tipos-despesa/editar", {"id": tipo["id"], "nome": "Prestação de serviços", "ativo": 1}, esperado=200)
            despesa = post("/api/despesas", {
                "setor_id": setor["id"], "tipo_despesa_id": tipo["id"],
                "descricao": "Manutenção mensal", "natureza": "FIXA", "recorrente": 1,
            })
            conta = post("/api/contas-pagar", {
                "despesa_id": despesa["id"], "data_vencimento": "2026-09-10", "valor": 100,
            })
            pagamento = post("/api/pagamentos-saida", {
                "conta_pagar_id": conta["id"], "data_pagamento": "2026-09-01",
                "valor": 40, "forma_pagamento": "PIX", "observacao": "Parcial",
            })
            self.assertEqual("PARCIAL", pagamento["status"])
            conexao.request("GET", f"/api/contas-pagar/pagamentos?id={conta['id']}")
            resposta = conexao.getresponse(); historico_saida = json.loads(resposta.read())
            self.assertEqual(200, resposta.status)
            self.assertEqual(1, len(historico_saida["dados"]))

            conexao.request("GET", "/api/contas-receber")
            resposta = conexao.getresponse(); cobrancas = json.loads(resposta.read())["dados"]
            cobranca = cobrancas[0]
            recebimento = post("/api/recebimentos", {
                "cobranca_id": cobranca["id"], "data_pagamento": "2026-09-01",
                "valor": 100, "observacao": "Recebimento parcial",
            })
            self.assertEqual("PIX", recebimentos.buscar_recebimento(recebimento["id"])["forma_recebimento"])
            desconto = post("/api/cobrancas/desconto", {
                "cobranca_id": cobranca["id"], "valor": 50,
            })
            self.assertEqual("PARCIAL", desconto["status"])
            conexao.request("GET", f"/api/contas-receber/recebimentos?id={cobranca['id']}")
            resposta = conexao.getresponse(); historico_entrada = json.loads(resposta.read())
            self.assertEqual(1, len(historico_entrada["dados"]))

            post("/api/pagamentos-saida/excluir", {"pagamento_id": pagamento["id"]}, esperado=200)
            post("/api/recebimentos/excluir", {"recebimento_id": recebimento["id"]}, esperado=200)
            post("/api/contas-pagar/cancelar", {"conta_id": conta["id"]}, esperado=200)
            produto = post("/api/itens", {
                "nome": "Suco", "codigo_barras": "7890000000001", "categoria": "Bebidas",
                "unidade_medida": "UN", "valor": 5, "estoque_inicial": 10,
                "estoque_minimo": 2, "data_inicio_valor": "2026-08-28", "ativo": 1,
            })
            carteira = post("/api/carteiras", {"residente_id": residente["id"], "saldo_inicial": 20})
            post("/api/carteiras/credito", {"carteira_id": carteira["id"], "valor": 10, "data_movimentacao": "2026-08-28"})
            conexao.request("GET", "/api/cantina/produto?codigo=7890000000001&data=2026-08-28")
            resposta = conexao.getresponse(); produto_lido = json.loads(resposta.read())
            self.assertEqual(200, resposta.status)
            self.assertTrue(produto_lido["dados"]["sucesso"])
            self.assertEqual(produto["id"], produto_lido["dados"]["id"])
            venda = post("/api/cantina/checkout", {
                "carteira_id": carteira["id"],
                "produtos": [
                    {"item_id": produto["id"], "quantidade": 1},
                    {"item_id": produto["id"], "quantidade": 1},
                ],
                "data_movimentacao": "2026-08-28",
            })
            self.assertEqual(10, venda["valor_total"])
            self.assertEqual(2, venda["quantidade_itens"])
            post("/api/cantina/vendas/estornar", {"venda_id": venda["id"], "motivo": "Correção"}, esperado=200)
            post("/api/carteiras/status", {"carteira_id": carteira["id"], "ativo": 0}, esperado=200)
            post("/api/carteiras/status", {"carteira_id": carteira["id"], "ativo": 1}, esperado=200)
            post("/api/itens/editar", {
                "id": produto["id"], "nome": "Suco natural", "categoria": "Bebidas",
                "unidade_medida": "UN", "estoque_minimo": 3, "ativo": 1,
            }, esperado=200)
            post("/api/itens/estoque", {
                "item_id": produto["id"], "tipo": "ENTRADA", "quantidade": 5,
                "motivo": "Reposição", "data_movimentacao": "2026-08-29",
                "custo_unitario": 3, "fornecedor": "Fornecedor Teste",
                "documento": "NF-456", "lote": "LOTE-02", "data_validade": "2027-02-01",
            })
            post("/api/itens/precos", {
                "item_id": produto["id"], "valor": 6, "data_inicio_valor": "2026-08-29",
            })
            conexao.request("GET", f"/api/itens/historico?id={produto['id']}")
            resposta = conexao.getresponse(); historico_produto = json.loads(resposta.read())
            self.assertEqual(2, len(historico_produto["dados"]["precos"]))
            entrada_estoque = next(
                movimento for movimento in historico_produto["dados"]["estoque"]
                if movimento["tipo"] == "ENTRADA"
            )
            self.assertEqual("Fornecedor Teste", entrada_estoque["fornecedor"])
            self.assertEqual("NF-456", entrada_estoque["documento"])
            post("/api/residentes/editar", {
                "id": residente["id"], "nome": "Residente Editado",
                "cpf": "11122233344", "cidade_origem": "Toledo",
            }, esperado=200)
            post("/api/responsaveis/editar", {
                "id": responsavel["id"], "nome": "Responsável Editado", "cpf": "55566677788",
                "telefone": "45999990000", "email": "responsavel@example.com", "ativo": 1,
            }, esperado=200)
            outro_responsavel = post("/api/responsaveis", {
                "nome": "Responsável Alternativo", "cpf": "22233344455",
            })
            post("/api/internacoes/responsavel", {
                "id": internacao["id"], "responsavel_id": outro_responsavel["id"],
            }, esperado=200)
            colaborador = post("/api/colaboradores", {
                "nome": "Colaborador Cadastro", "cpf": "99988877766",
                "senha": "senha-segura", "status": "ATIVO",
            })
            post("/api/colaboradores/editar", {
                "id": colaborador["id"], "nome": "Colaborador Editado",
                "cpf": "99988877766", "status": "ATIVO",
            }, esperado=200)
            post("/api/colaboradores/senha", {
                "id": colaborador["id"], "senha": "nova-senha-segura",
            }, esperado=200)
            post("/api/internacoes/encerrar", {
                "id": internacao["id"], "data_encerramento": "2026-08-29", "motivo": "Alta",
            }, esperado=200)
        finally:
            conexao.close(); servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

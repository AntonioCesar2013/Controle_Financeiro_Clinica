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
from src.servidor import Requisicao, SESSOES


class TestIntegracaoFrontend(unittest.TestCase):
    def setUp(self):
        self.diretorio = tempfile.TemporaryDirectory()
        self.caminho_banco = Path(self.diretorio.name) / "clinica.db"
        self.patch_caminho = patch.object(banco, "CAMINHO_BANCO", self.caminho_banco)
        self.patch_caminho.start()
        banco.criar_tabelas()

    def tearDown(self):
        SESSOES.clear()
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
        finally:
            conexao.close()
            servidor.shutdown()
            servidor.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

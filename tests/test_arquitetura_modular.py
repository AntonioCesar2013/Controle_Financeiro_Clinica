import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from src.infraestrutura import banco
from src.nucleo.migracoes import Migracao, aplicar_migracoes, preparar_controle
from src.nucleo.modulos import modulos_registrados, permissoes_disponiveis


class ArquiteturaModular(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory(prefix="arquitetura_clinica_")
        self.addCleanup(self.pasta.cleanup)
        caminho = Path(self.pasta.name) / "teste.db"
        self.patch_banco = patch.object(banco, "CAMINHO_BANCO", caminho)
        self.patch_banco.start()
        self.addCleanup(self.patch_banco.stop)

    def test_registro_e_permissoes_de_extensao(self):
        self.assertEqual([m.nome for m in modulos_registrados()], ["cadastros", "financeiro", "cantina"])
        self.assertIn("financeiro.receber", permissoes_disponiveis())
        self.assertIn("cantina.vender", permissoes_disponiveis())

    def test_preparacao_repetivel_aplica_migracoes_uma_vez(self):
        banco.criar_tabelas()
        banco.criar_tabelas()
        with closing(banco.conectar()) as conexao:
            linhas = conexao.execute(
                "SELECT modulo,versao FROM migracoes_schema ORDER BY modulo"
            ).fetchall()
        self.assertEqual(linhas, [("cadastros", 1), ("cantina", 1), ("financeiro", 1), ("financeiro", 2)])

    def test_migracoes_futuras_fazem_rollback_com_transacao_externa(self):
        conexao = sqlite3.connect(":memory:")
        preparar_controle(conexao)

        def falhar(conn):
            conn.execute("CREATE TABLE temporaria(id INTEGER)")
            raise RuntimeError("falha simulada")

        with self.assertRaises(RuntimeError):
            with conexao:
                aplicar_migracoes(conexao, [Migracao("teste", 1, falhar)])
        self.assertIsNone(conexao.execute(
            "SELECT name FROM sqlite_master WHERE name='temporaria'"
        ).fetchone())
        self.assertEqual(conexao.execute("SELECT COUNT(*) FROM migracoes_schema").fetchone()[0], 0)

    def test_rotas_get_publicas_continuam_registradas(self):
        from src.interface.rotas import rotas_get

        rotas = rotas_get({})
        esperadas = {
            "/api/residentes", "/api/internacoes", "/api/contas-receber",
            "/api/contas-pagar", "/api/cantina", "/api/itens", "/api/relatorios",
        }
        self.assertTrue(esperadas.issubset(rotas))

    def test_entradas_antigas_encaminham_para_implementacoes_atuais(self):
        import src.banco as banco_compativel
        import src.servidor as servidor_compativel
        from src.interface import servidor

        self.assertIs(banco_compativel.criar_tabelas, banco.criar_tabelas)
        self.assertIs(servidor_compativel.Requisicao, servidor.Requisicao)

    def test_importacoes_publicas_nao_formam_ciclo(self):
        import importlib

        for nome in (
            "src.financeiro.api_publica",
            "src.cantina.api_publica",
            "src.cadastros.internacoes",
            "src.interface.rotas",
        ):
            self.assertIsNotNone(importlib.import_module(nome))

    def test_falha_financeira_reverte_cadastro_compartilhado(self):
        from datetime import date
        from src.cadastros import internacoes

        banco.criar_tabelas()
        with closing(banco.conectar()) as conexao, conexao:
            residente = conexao.execute(
                "INSERT INTO residentes(nome,cpf) VALUES('Teste','1')"
            ).lastrowid
            responsavel = conexao.execute(
                "INSERT INTO responsaveis(nome,cpf) VALUES('Resp','2')"
            ).lastrowid
        with patch.object(
            internacoes,
            "criar_contrato_internacao",
            side_effect=RuntimeError("falha financeira simulada"),
        ):
            resultado = internacoes.cadastrar_internacao_com_cobrancas(
                residente, responsavel, date.today().isoformat(), 1, 0, 0, 0
            )
        self.assertFalse(resultado["sucesso"])
        with closing(banco.conectar()) as conexao:
            self.assertEqual(conexao.execute("SELECT COUNT(*) FROM internacoes").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()

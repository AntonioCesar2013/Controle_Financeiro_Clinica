import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import banco


class TestSchemaColaboradores(unittest.TestCase):
    def setUp(self):
        self.diretorio = tempfile.TemporaryDirectory()
        self.caminho_banco = Path(self.diretorio.name) / "clinica.db"
        self.patch_caminho = patch.object(banco, "CAMINHO_BANCO", self.caminho_banco)
        self.patch_caminho.start()
        banco.criar_tabelas()

    def tearDown(self):
        self.patch_caminho.stop()
        self.diretorio.cleanup()

    def test_cria_tabela_com_campos_e_restricoes_esperados(self):
        conexao = sqlite3.connect(self.caminho_banco)
        try:
            colunas = {
                linha[1]: linha
                for linha in conexao.execute("PRAGMA table_info(colaboradores)")
            }

            self.assertEqual(
                {
                    "id",
                    "nome",
                    "cpf",
                    "senha_hash",
                    "status",
                    "criado_em",
                    "atualizado_em",
                },
                set(colunas),
            )
            self.assertEqual(1, colunas["nome"][3])
            self.assertEqual(1, colunas["cpf"][3])
            self.assertEqual(1, colunas["senha_hash"][3])
            self.assertEqual(1, colunas["status"][3])
        finally:
            conexao.close()

    def test_impede_cpf_duplicado_e_status_invalido(self):
        conexao = sqlite3.connect(self.caminho_banco)
        try:
            conexao.execute(
                """
                INSERT INTO colaboradores (nome, cpf, senha_hash)
                VALUES (?, ?, ?)
                """,
                ("Maria Oliveira", "12345678900", "hash-de-teste"),
            )

            with self.assertRaises(sqlite3.IntegrityError):
                conexao.execute(
                    """
                    INSERT INTO colaboradores (nome, cpf, senha_hash)
                    VALUES (?, ?, ?)
                    """,
                    ("Outra Maria", "12345678900", "outro-hash"),
                )

            with self.assertRaises(sqlite3.IntegrityError):
                conexao.execute(
                    """
                    INSERT INTO colaboradores (nome, cpf, senha_hash, status)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("João Santos", "98765432100", "hash-de-teste", "BLOQUEADO"),
                )
        finally:
            conexao.close()


if __name__ == "__main__":
    unittest.main()

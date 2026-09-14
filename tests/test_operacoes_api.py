"""Proteção persistente das gravações em banco descartável."""
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from src.infraestrutura import banco, operacoes


class OperacoesApiTests(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory(prefix="operacoes_api_")
        self.addCleanup(pasta.cleanup)
        self.patch_banco = patch.object(banco, "CAMINHO_BANCO", Path(pasta.name) / "teste.db")
        self.patch_banco.start()
        self.addCleanup(self.patch_banco.stop)
        banco.criar_tabelas()

    def test_reenvio_retorna_resultado_sem_duplicar_e_recusa_dados_diferentes(self):
        execucoes = 0

        def gravar():
            nonlocal execucoes
            execucoes += 1
            conn = banco.conectar()
            cursor = conn.execute("INSERT INTO responsaveis(nome,cpf) VALUES('Idempotente','12345678901')")
            return ({"sucesso": True, "id": cursor.lastrowid}, 201, None)

        chave = "operacao_servidor_0001"
        primeiro = operacoes.executar(chave, "/api/responsaveis", {"cpf": "12345678901"}, gravar)
        segundo = operacoes.executar(chave, "/api/responsaveis", {"cpf": "12345678901"}, gravar)
        self.assertEqual(primeiro, segundo)
        self.assertEqual(execucoes, 1)
        with closing(banco.conectar()) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM responsaveis").fetchone()[0], 1)
        with self.assertRaises(operacoes.ConflitoOperacao):
            operacoes.executar(chave, "/api/responsaveis", {"cpf": "outro"}, gravar)

    def test_cancelamento_reserva_chave_sem_simular_estorno(self):
        chave = "operacao_cancelada_0001"
        self.assertEqual(operacoes.cancelar(chave)["estado"], "CANCELADA")
        self.assertEqual(operacoes.consultar(chave)["estado"], "CANCELADA")
        with self.assertRaises(operacoes.ConflitoOperacao):
            operacoes.executar(chave, "/api/responsaveis", {"cpf": "1"},
                               lambda: ({"sucesso": True}, 200, None))


if __name__ == "__main__":
    unittest.main()

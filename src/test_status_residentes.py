import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src import internacoes
from src.banco import CAMINHO_BANCO


class StatusResidentesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.banco = Path(self.temp.name) / "status.db"
        origem = sqlite3.connect(CAMINHO_BANCO)
        destino = sqlite3.connect(self.banco)
        origem.backup(destino); origem.close(); destino.close()
        conn = sqlite3.connect(self.banco)
        for tabela in ("recebimentos", "cobrancas", "internacoes", "residente_responsavel", "responsaveis", "residentes"):
            conn.execute(f"DELETE FROM {tabela}")
            conn.execute("DELETE FROM sqlite_sequence WHERE name=?", (tabela,))
        for indice in range(1, 4):
            conn.execute("INSERT INTO residentes(nome,cpf,ativo) VALUES (?,?,0)", (f"Residente {indice}", f"9000000000{indice}"))
        conn.execute("INSERT INTO responsaveis(nome,cpf) VALUES ('Responsável','80000000001')")
        conn.commit(); conn.close()
        self.patcher = patch("src.internacoes.conectar", side_effect=lambda: sqlite3.connect(self.banco))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop(); self.temp.cleanup()

    def test_ativo_apenas_dentro_do_periodo_da_internacao(self):
        hoje = date.today().isoformat()
        internacoes.cadastrar_internacao(1, 1, hoje, 1, 10000, 1000, 9000)
        internacoes.cadastrar_internacao(2, 1, "2020-01-01", 1, 10000, 1000, 9000)
        internacoes.cadastrar_internacao(3, 1, "2030-01-01", 1, 10000, 1000, 9000)
        internacoes.sincronizar_status_residentes(hoje)
        conn = sqlite3.connect(self.banco)
        estados = conn.execute("SELECT id,ativo FROM residentes ORDER BY id").fetchall()
        status = conn.execute("SELECT residente_id,status FROM internacoes ORDER BY residente_id").fetchall()
        conn.close()
        self.assertEqual(estados, [(1, 1), (2, 0), (3, 0)])
        self.assertEqual(status, [(1, "ATIVA"), (2, "ENCERRADA"), (3, "ENCERRADA")])


if __name__ == "__main__":
    unittest.main()

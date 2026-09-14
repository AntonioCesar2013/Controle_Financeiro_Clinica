"""Cliente JavaScript real contra servidor HTTP e banco descartável."""
import json
import subprocess
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from src.infraestrutura import banco
from src.infraestrutura.backup.config import BackupConfig
from src.infraestrutura.backup.service import BackupService
from src.interface.servidor import criar_servidor


class ApiFrontendIntegracaoTests(unittest.TestCase):
    def test_resposta_perdida_recupera_resultado_sem_duplicar(self):
        with tempfile.TemporaryDirectory(prefix="api_frontend_") as pasta:
            caminho = Path(pasta) / "clinica.db"
            config = BackupConfig(Path(pasta) / "config")
            config.save({"backup_directory": str(Path(pasta) / "backups")})
            service_factory = lambda source: BackupService(source, config=config)
            with patch.object(banco, "CAMINHO_BANCO", caminho), \
                 patch("src.interface.servidor.BackupService", side_effect=service_factory):
                servidor, endereco, _ = criar_servidor("127.0.0.1", 0)
                endereco = f"http://127.0.0.1:{servidor.server_port}/"
                thread = threading.Thread(target=servidor.serve_forever, daemon=True)
                thread.start()
                try:
                    script = Path(__file__).parent / "support" / "api_http_client.mjs"
                    processo = subprocess.run(
                        ["node", str(script), endereco], capture_output=True, text=True,
                        timeout=20, check=True,
                    )
                    resultado = json.loads(processo.stdout)
                    self.assertTrue(resultado["result"]["sucesso"])
                    self.assertRegex(resultado["sentKey"], r"^[A-Za-z0-9_-]{16,128}$")
                    with closing(banco.conectar()) as conexao:
                        self.assertEqual(conexao.execute(
                            "SELECT COUNT(*) FROM responsaveis WHERE cpf='45678901234'"
                        ).fetchone()[0], 1)
                        self.assertEqual(conexao.execute(
                            "SELECT COUNT(*) FROM operacoes_api WHERE chave=?",
                            (resultado["sentKey"],),
                        ).fetchone()[0], 1)
                finally:
                    servidor.shutdown()
                    servidor.server_close()
                    thread.join(2)


if __name__ == "__main__":
    unittest.main()

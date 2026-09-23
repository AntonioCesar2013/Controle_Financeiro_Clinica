"""Catálogo e restauração exercitados somente com bancos temporários."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from src.infraestrutura import banco, backup_banco
from src.infraestrutura.backup.config import BackupConfig
from src.infraestrutura.backup.snapshot import create_compressed_snapshot, create_snapshot
from src.infraestrutura.backup.service import BackupService
from src.infraestrutura.uso_banco import BancoEmUsoError, TravaUsoBanco


class RecuperacaoBackupTests(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory(prefix="backup_recuperacao_")
        self.addCleanup(pasta.cleanup)
        self.raiz = Path(pasta.name)
        self.banco = self.raiz / "dados" / "clinica.db"
        self.legados = self.raiz / "dados" / "backups"
        self.novos = self.raiz / "configurados"
        self.config = BackupConfig(self.raiz / "config")
        self.config.save({"backup_directory": str(self.novos)})
        self.patch_banco = patch.object(banco, "CAMINHO_BANCO", self.banco)
        self.patch_pasta = patch.object(backup_banco, "PASTA_BACKUPS", self.legados)
        self.patch_banco.start()
        self.patch_pasta.start()
        self.addCleanup(self.patch_banco.stop)
        self.addCleanup(self.patch_pasta.stop)
        banco.criar_tabelas()
        with closing(sqlite3.connect(self.banco)) as conn, conn:
            conn.execute("INSERT INTO residentes(nome,cpf) VALUES('Atual','11111111111')")

    def _copia(self, pasta, nome, residente):
        with closing(sqlite3.connect(self.banco)) as conn, conn:
            conn.execute("UPDATE residentes SET nome=?", (residente,))
        return create_snapshot(self.banco, pasta / nome)

    def test_catalogo_reconhece_formatos_e_pasta_configurada(self):
        antigo = self._copia(self.legados, "clinica_20260913_manual.db", "Antigo")
        novo = self._copia(self.novos, "controle_financeiro_2026-09-13_120000_1.db", "Novo")
        self.assertEqual(set(backup_banco.listar_backups(self.config)), {antigo.resolve(), novo.resolve()})

    def test_restaura_novo_formato_e_preserva_copia_anterior(self):
        origem = self._copia(self.novos, "controle_financeiro_2026-09-13_120000_2.db", "Restaurado")
        with closing(sqlite3.connect(self.banco)) as conn, conn:
            conn.execute("UPDATE residentes SET nome='Antes da restauração'")
        resultado = backup_banco.restaurar_backup(origem.name, self.config)
        with closing(sqlite3.connect(self.banco)) as conn:
            self.assertEqual(conn.execute("SELECT nome FROM residentes").fetchone()[0], "Restaurado")
        with closing(sqlite3.connect(resultado["backup_anterior"])) as conn:
            self.assertEqual(conn.execute("SELECT nome FROM residentes").fetchone()[0], "Antes da restauração")

    def test_restaura_backup_compactado(self):
        with closing(sqlite3.connect(self.banco)) as conn, conn:
            conn.execute("UPDATE residentes SET nome='Restaurado do gzip'")
        origem = create_compressed_snapshot(
            self.banco, self.novos / "controle_financeiro_2026-09-22_120000_1.db.gz"
        )
        with closing(sqlite3.connect(self.banco)) as conn, conn:
            conn.execute("UPDATE residentes SET nome='Antes da restauração gzip'")
        resultado = backup_banco.restaurar_backup(origem.name, self.config)
        with closing(sqlite3.connect(self.banco)) as conn:
            self.assertEqual(conn.execute("SELECT nome FROM residentes").fetchone()[0], "Restaurado do gzip")
        with closing(sqlite3.connect(resultado["backup_anterior"])) as conn:
            self.assertEqual(conn.execute("SELECT nome FROM residentes").fetchone()[0], "Antes da restauração gzip")

    def test_invalido_ou_incompativel_nao_modifica_banco(self):
        invalido = self.novos / "controle_financeiro_invalido.db"
        invalido.parent.mkdir(parents=True)
        invalido.write_bytes(b"arquivo invalido")
        antes = self.banco.read_bytes()
        with self.assertRaises(ValueError):
            backup_banco.restaurar_backup(invalido.name, self.config)
        self.assertEqual(self.banco.read_bytes(), antes)

        incompativel = self.novos / "controle_financeiro_outro.db"
        with closing(sqlite3.connect(incompativel)) as conn, conn:
            conn.execute("CREATE TABLE outra(id INTEGER)")
        with self.assertRaises(ValueError):
            backup_banco.restaurar_backup(incompativel.name, self.config)
        self.assertEqual(self.banco.read_bytes(), antes)

    def test_restauração_bloqueada_enquanto_sistema_usa_banco(self):
        origem = self._copia(self.novos, "controle_financeiro_bloqueio.db", "Cópia")
        trava = TravaUsoBanco(self.banco).adquirir()
        try:
            with self.assertRaises(BancoEmUsoError):
                backup_banco.restaurar_backup(origem.name, self.config)
        finally:
            trava.liberar()

    def test_estados_operacionais_desativado_ausente_atrasado_e_em_dia(self):
        service = BackupService(self.banco, self.config)
        self.assertEqual(service.status()["automatic_state"], "DESATIVADO")
        self.config.save({"backup_enabled": True, "interval_hours": 6})
        self.assertEqual(service.status()["automatic_state"], "NUNCA_CONCLUIDO")
        service._update(last_success=(datetime.now(timezone.utc)-timedelta(hours=7)).isoformat())
        self.assertEqual(service.status()["automatic_state"], "ATRASADO")
        service._update(last_success=datetime.now(timezone.utc).isoformat(),
                        last_r2_success="2026-09-13T12:00:00+00:00")
        status = service.status()
        self.assertEqual(status["automatic_state"], "EM_DIA")
        self.assertEqual(status["last_r2_success"], "2026-09-13T12:00:00+00:00")

    def test_estado_parcial_quando_destino_externo_nao_recebeu_snapshot_atual(self):
        service = BackupService(self.banco, self.config)
        self.config.save({
            "backup_enabled": True,
            "interval_hours": 6,
            "r2_enabled": True,
            "r2_bucket": "bucket",
            "r2_endpoint": "https://" + "a" * 32 + ".r2.cloudflarestorage.com",
        })
        service._update(
            last_success=datetime.now(timezone.utc).isoformat(),
            last_r2_success=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        )
        status = service.status()
        self.assertEqual(status["automatic_state"], "PARCIAL")
        self.assertEqual(status["external_pending"], ["r2"])
        service._update(last_r2_success=datetime.now(timezone.utc).isoformat())
        self.assertEqual(service.status()["automatic_state"], "EM_DIA")


if __name__ == "__main__":
    unittest.main()

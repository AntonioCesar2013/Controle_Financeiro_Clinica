"""Inicialização e liberação de recursos sem abrir a janela nem o banco real."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import main
from src.infraestrutura import banco
from src.infraestrutura.uso_banco import BancoEmUsoError, TravaUsoBanco
from src.infraestrutura.backup.config import BackupConfig
from src.infraestrutura.backup.service import BackupService
from src.interface import servidor


class InicializacaoTests(unittest.TestCase):
    def test_dependencia_backup_ausente_orienta_instalacao(self):
        erro = ModuleNotFoundError("ausente", name="platformdirs")
        with patch.dict('sys.modules', webview=Mock()), patch.object(
            main, 'criar_servidor', side_effect=erro
        ), self.assertRaisesRegex(SystemExit, 'platformdirs.*iniciar.cmd'):
            main.main()

    def test_falha_janela_fecha_servidor(self):
        http = Mock()
        view = Mock()
        view.create_window.side_effect = RuntimeError('falha de janela')
        with patch.dict('sys.modules', webview=view), patch.object(
            main, 'criar_servidor', return_value=(http, 'http://127.0.0.1', '')
        ), self.assertRaisesRegex(SystemExit, 'WebView2'):
            main.main()
        http.shutdown.assert_called_once()
        http.server_close.assert_called_once()

    def test_falha_backup_libera_porta(self):
        http = Mock()
        trava = Mock()
        trava.adquirir.return_value = trava
        with patch.object(servidor, 'TravaUsoBanco', return_value=trava), patch.object(
            servidor, 'criar_tabelas'
        ), patch.object(
            servidor, 'sincronizar_status_residentes'
        ), patch.object(servidor, 'ServidorClinica', return_value=http), patch.object(
            servidor, 'BackupService', side_effect=ModuleNotFoundError(name='platformdirs')
        ), self.assertRaises(ModuleNotFoundError):
            servidor.criar_servidor(porta=0)
        http.server_close.assert_called_once()

    def test_banco_em_uso_bloqueia_antes_de_migrar(self):
        with tempfile.TemporaryDirectory() as directory:
            caminho = Path(directory) / 'clinica.db'
            primeira = TravaUsoBanco(caminho).adquirir()
            try:
                with patch.object(banco, 'CAMINHO_BANCO', caminho), patch.object(
                    servidor, 'criar_tabelas'
                ) as migrar, patch.object(
                    servidor, 'sincronizar_status_residentes'
                ) as sincronizar, self.assertRaises(BancoEmUsoError):
                    servidor.criar_servidor(porta=0)
                migrar.assert_not_called()
                sincronizar.assert_not_called()
                self.assertFalse(caminho.exists())
            finally:
                primeira.liberar()

    def test_falha_antes_da_porta_libera_trava(self):
        with tempfile.TemporaryDirectory() as directory:
            caminho = Path(directory) / 'clinica.db'
            with patch.object(banco, 'CAMINHO_BANCO', caminho), patch.object(
                servidor, 'criar_tabelas', side_effect=RuntimeError('falha de migração')
            ), self.assertRaisesRegex(RuntimeError, 'falha de migração'):
                servidor.criar_servidor(porta=0)
            segunda = TravaUsoBanco(caminho).adquirir()
            segunda.liberar()

    def test_servidor_com_backup_em_banco_temporario(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = BackupService(root / 'teste.db', config=BackupConfig(root / 'config'))
            with patch.object(banco, 'CAMINHO_BANCO', service.source), patch.object(
                servidor, 'BackupService', return_value=service
            ):
                http, _, _ = servidor.criar_servidor(porta=0)
                try:
                    self.assertTrue(http.backup_scheduler.thread.is_alive())
                    self.assertFalse(service.config.load()['backup_enabled'])
                finally:
                    http.server_close()
                self.assertFalse(http.backup_scheduler.thread.is_alive())

"""Inicialização e liberação de recursos sem abrir a janela nem o banco real."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import main
from src.infraestrutura import banco
from src.infraestrutura.uso_banco import BancoEmUsoError, TravaUsoBanco
from src.infraestrutura.backup.config import BackupConfig
from src.infraestrutura.backup.service import BackupService
from src.interface import servidor


class InicializacaoTests(unittest.TestCase):
    def test_servidor_limita_threads_residentes(self):
        self.assertEqual(servidor.ServidorClinica.MAXIMO_REQUISICOES_SIMULTANEAS, 8)
        self.assertTrue(servidor.ServidorClinica.daemon_threads)
        self.assertFalse(servidor.ServidorClinica.block_on_close)

    def tearDown(self):
        with servidor.LOCK_SESSOES:
            servidor.SESSOES.clear()

    def test_sessoes_expiram_e_possuem_limite_de_memoria(self):
        with servidor.LOCK_SESSOES:
            for indice in range(servidor.SESSOES_LIMITE + 5):
                servidor.SESSOES[str(indice)] = {
                    'colaborador': {'id': indice}, 'ultimo_acesso': float(indice),
                }
            servidor._limpar_sessoes(servidor.SESSAO_TEMPO_LIMITE + servidor.SESSOES_LIMITE + 4)
            self.assertLessEqual(len(servidor.SESSOES), servidor.SESSOES_LIMITE)

    def test_consulta_de_sessao_renova_ultimo_acesso(self):
        token = 'token-teste'
        with servidor.LOCK_SESSOES:
            servidor.SESSOES[token] = {'colaborador': {'id': 7}, 'ultimo_acesso': 1.0}
        requisicao = object.__new__(servidor.Requisicao)
        requisicao.headers = {'Cookie': f'sessao={token}'}
        with patch.object(servidor.time, 'monotonic', return_value=2.0):
            self.assertEqual(requisicao._sessao(), {'id': 7})
        self.assertEqual(servidor.SESSOES[token]['ultimo_acesso'], 2.0)

    def test_inicializador_nao_mantem_powershell_residente(self):
        script = (Path(__file__).resolve().parents[1] / 'iniciar.ps1').read_text(encoding='utf-8')
        linha_processo = next(linha for linha in script.splitlines() if '$processo = Start-Process' in linha)
        self.assertNotIn('-Wait', linha_processo)
        self.assertIn('WaitForExit(5000)', script)
        self.assertIn('if (-not $encerrouNaPartida)', script)

    def test_webview2_usa_perfil_economico_sem_sobrescrever_configuracao_externa(self):
        with patch.dict(os.environ, {}, clear=True):
            main.configurar_webview2_economico()
            argumentos = os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS']
            self.assertIn('--renderer-process-limit=1', argumentos)
            self.assertIn('--disable-background-networking', argumentos)

        with patch.dict(os.environ, {'WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS': '--opcao-personalizada'}, clear=True):
            main.configurar_webview2_economico()
            self.assertEqual(os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'], '--opcao-personalizada')

    def test_janela_define_identidade_e_icone_proprios_no_windows(self):
        self.assertTrue(main.caminho_icone().is_file())
        with patch.object(main.sys, 'platform', 'win32'), patch.object(main.ctypes, 'windll') as winapi:
            winapi.user32.FindWindowW.return_value = 123
            winapi.user32.LoadImageW.return_value = 456
            main.configurar_identidade_windows()
            main.aplicar_icone_janela_windows()
        winapi.shell32.SetCurrentProcessExplicitAppUserModelID.assert_called_once_with(main.ID_APLICATIVO_WINDOWS)
        winapi.user32.FindWindowW.assert_called_once_with(None, main.TITULO_JANELA)
        self.assertEqual(winapi.user32.SendMessageW.call_count, 2)

    def test_janela_principal_inicia_maximizada(self):
        http = Mock()
        janela = MagicMock()
        view = Mock()
        view.create_window.return_value = janela
        with patch.dict('sys.modules', webview=view), patch.object(
            main, 'criar_servidor', return_value=(http, 'http://127.0.0.1', '')
        ):
            main.main()
        self.assertTrue(view.create_window.call_args.kwargs['maximized'])

    def test_segunda_instancia_retorna_codigo_especifico(self):
        with patch.dict('sys.modules', webview=Mock()), patch.object(
            main, 'criar_servidor', side_effect=BancoEmUsoError('em uso')
        ), self.assertRaises(SystemExit) as caught:
            main.main()
        self.assertEqual(caught.exception.code, 2)

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

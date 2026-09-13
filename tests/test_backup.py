import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from contextlib import closing

from src.infraestrutura.backup.config import BackupConfig, DEFAULTS
from src.infraestrutura.backup.credentials import CredentialService
from src.infraestrutura.backup.snapshot import create_snapshot
from src.infraestrutura.backup.service import BackupService
from src.infraestrutura.backup.providers.base import retry
from src.infraestrutura.backup.providers.r2 import R2Provider
from src.infraestrutura.backup.providers.drive import DriveProvider


class BackupTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / 'source.db'
        with closing(sqlite3.connect(self.source)) as connection:
            connection.execute('CREATE TABLE dados(valor TEXT)')
            connection.execute("INSERT INTO dados VALUES ('teste')")
            connection.commit()
        self.config = BackupConfig(self.root / 'config')
        self.config.save({'backup_directory': str(self.root / 'backups')})
        self.vault = Mock()
        self.vault.get_password.return_value = None
        self.credentials = CredentialService(self.vault)

    def test_snapshot_consistente(self):
        path = create_snapshot(self.source, self.root / 'backup.db')
        with closing(sqlite3.connect(path)) as connection:
            self.assertEqual(connection.execute('SELECT valor FROM dados').fetchone(), ('teste',))
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone(), ('ok',))
        self.assertFalse(list(self.root.glob('*.tmp')))

    def test_snapshot_wal(self):
        connection = sqlite3.connect(self.source)
        self.addCleanup(connection.close)
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute("INSERT INTO dados VALUES ('wal')")
        connection.commit()
        path = create_snapshot(self.source, self.root / 'wal.db')
        with closing(sqlite3.connect(path)) as backup:
            self.assertEqual(backup.execute('SELECT COUNT(*) FROM dados').fetchone()[0], 2)

    def test_snapshot_invalido_excluido(self):
        self.source.write_bytes(b'invalid sqlite')
        with self.assertRaises(sqlite3.DatabaseError):
            create_snapshot(self.source, self.root / 'invalid.db')
        self.assertFalse((self.root / 'invalid.db').exists())
        self.assertFalse(list(self.root.glob('*.tmp')))

    def test_banco_ausente_nao_cria_banco(self):
        missing = self.root / 'missing.db'
        with self.assertRaises(FileNotFoundError):
            create_snapshot(missing, self.root / 'copy.db')
        self.assertFalse(missing.exists())

    def test_config_defaults_invalidos_campos_antigos(self):
        store = BackupConfig(self.root / 'new')
        self.assertEqual(store.load(), DEFAULTS)
        store.save({'interval_hours': 12, 'old_field': 'ignored', 'secret': 'NEVER'})
        self.assertEqual(store.load()['interval_hours'], 12)
        self.assertNotIn('NEVER', store.path.read_text())
        store.path.write_text('{invalid')
        self.assertEqual(store.load(), DEFAULTS)
        for value in (0, -1, float('nan'), True, '6'):
            with self.assertRaises(ValueError):
                store.save({'interval_hours': value})

    def test_secrets_somente_vault(self):
        service = BackupService(self.source, self.config, self.credentials)
        response = service.save_settings({'credentials': {'r2_secret_access_key': 'PRIVATE_SENTINEL'}})
        self.vault.set_password.assert_called_once_with('Controle_Financeiro_Clinica.Backup', 'r2_secret_access_key', 'PRIVATE_SENTINEL')
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(response))
        self.assertNotIn('PRIVATE_SENTINEL', self.config.path.read_text())

    def test_destinos_independentes(self):
        self.config.save({'r2_enabled': True, 'r2_bucket': 'bucket',
                          'r2_endpoint': 'https://' + 'a' * 32 + '.r2.cloudflarestorage.com', 'drive_enabled': True})
        service = BackupService(self.source, self.config, self.credentials)
        r2, drive = Mock(), Mock()
        r2.upload_backup.side_effect = RuntimeError('PRIVATE_SENTINEL')
        service.providers.update(r2=r2, drive=drive)
        self.assertTrue(service.start())
        service.worker.join(5)
        result = service.status()['result']
        self.assertEqual((result['local'], result['r2'], result['drive']), ('success', 'failed', 'success'))
        drive.upload_backup.assert_called_once()
        self.assertTrue((self.root / 'backups' / result['filename']).is_file())
        self.assertNotIn('PRIVATE_SENTINEL', service.status_path.read_text())

    def test_lock_nao_permite_simultaneidade(self):
        service = BackupService(self.source, self.config, self.credentials)
        service.lock.acquire()
        try:
            self.assertFalse(service.start())
            self.assertIn('last_skipped', service.status())
        finally:
            service.lock.release()

    def test_falha_local_nao_envia_nuvem(self):
        service = BackupService(self.root / 'missing', self.config, self.credentials)
        service.providers['r2'] = Mock()
        service.start()
        service.worker.join(5)
        self.assertEqual(service.status()['result']['local'], 'failed')
        service.providers['r2'].upload_backup.assert_not_called()

    def test_retry_limitado(self):
        operation = Mock(side_effect=[TimeoutError(), TimeoutError(), 'ok'])
        sleep = Mock()
        self.assertEqual(retry(operation, sleep), 'ok')
        self.assertEqual(operation.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])
        operation = Mock(side_effect=TimeoutError())
        with self.assertRaises(TimeoutError):
            retry(operation, Mock())
        self.assertEqual(operation.call_count, 3)

    def test_r2_upload_test_and_retry(self):
        from botocore.exceptions import ClientError
        self.vault.get_password.return_value = 'fake'
        config = self.config.save({'r2_endpoint': 'https://' + 'a' * 32 + '.r2.cloudflarestorage.com', 'r2_bucket': 'bucket'})
        provider = R2Provider(self.credentials)
        client = Mock()
        with patch('boto3.client', return_value=client):
            provider.upload_backup(self.source, config)
            provider.test_connection(config)
        self.assertTrue(client.put_object.call_args.kwargs['Key'].endswith(self.source.name))
        error = ClientError({'Error': {'Code': 'AccessDenied'}, 'ResponseMetadata': {'HTTPStatusCode': 403}}, 'PutObject')
        client.put_object.reset_mock()
        client.put_object.side_effect = error
        with patch('boto3.client', return_value=client), self.assertRaises(ClientError):
            provider.upload_backup(self.source, config)
        self.assertEqual(client.put_object.call_count, 1)
        client.put_object.side_effect = [TimeoutError(), None]
        with patch('boto3.client', return_value=client), patch('src.infraestrutura.backup.providers.r2.retry', side_effect=lambda op: retry(op, Mock())):
            provider.upload_backup(self.source, config)

    def test_drive_ausente_revogado_upload_retry(self):
        from google.auth.exceptions import RefreshError
        provider = DriveProvider(self.credentials, self.config)
        with self.assertRaises(ValueError):
            provider._api()
        self.vault.get_password.return_value = '{}'
        token = Mock(valid=False)
        token.refresh.side_effect = RefreshError('revoked')
        with patch('google.oauth2.credentials.Credentials.from_authorized_user_info', return_value=token), self.assertRaises(RefreshError):
            provider._api()
        self.assertEqual(token.refresh.call_count, 1)
        api = Mock()
        api.files().create().next_chunk.side_effect = [TimeoutError(), (None, {'id': 'uploaded'})]
        with patch.object(provider, '_api', return_value=api), patch.object(provider, '_folder', return_value='folder'), patch('src.infraestrutura.backup.providers.drive.retry', side_effect=lambda op: retry(op, Mock())):
            provider.upload_backup(self.source, self.config.load())
        self.assertEqual(api.files().create().next_chunk.call_count, 2)
        api.files().create().next_chunk.side_effect = ValueError('failed')
        with patch.object(provider, '_api', return_value=api), patch.object(provider, '_folder', return_value='folder'), self.assertRaises(ValueError):
            provider.upload_backup(self.source, self.config.load())

    def test_rotas_exigem_sessao_e_permissao(self):
        from src.interface.rotas.backup import dispatch
        handler = Mock()
        handler._sessao.return_value = None
        dispatch(handler, '/api/backup/config')
        self.assertEqual(handler._json.call_args.args[1], 401)
        handler._sessao.return_value = {'id': 1}
        with patch('src.nucleo.permissoes.permitido', return_value=False):
            dispatch(handler, '/api/backup/config')
        self.assertEqual(handler._json.call_args.args[1], 403)

    def test_integrity_check_recusado_nao_publica(self):
        target = Mock()
        target.execute.return_value.fetchall.return_value = [('corrupt',)]
        origin, output = Mock(), Mock()
        with patch('src.infraestrutura.backup.snapshot.sqlite3.connect', side_effect=[origin, output, target]):
            with self.assertRaises(ValueError):
                create_snapshot(self.source, self.root / 'refused.db')
        self.assertFalse((self.root / 'refused.db').exists())
        self.assertFalse(list(self.root.glob('*.tmp')))

    def test_scheduler_dispara_e_encerra(self):
        from src.infraestrutura.backup.scheduler import BackupScheduler
        service = Mock()
        service.config.load.return_value = {**DEFAULTS, 'backup_enabled': True}
        service.status.return_value = {}
        fired = threading.Event()
        service.start.side_effect = fired.set
        scheduler = BackupScheduler(service)
        scheduler.start()
        self.assertTrue(fired.wait(2))
        scheduler.stop()
        self.assertFalse(scheduler.thread.is_alive())

    def test_sdk_logs_nao_propagam_segredos(self):
        import logging
        from src.infraestrutura.backup.security import protect_sdk_logs
        protect_sdk_logs()
        handler = Mock(spec=logging.Handler)
        handler.level = logging.DEBUG
        root = logging.getLogger()
        root.addHandler(handler)
        try:
            logging.getLogger('google_auth_oauthlib.flow').error('PRIVATE_SENTINEL')
            handler.handle.assert_not_called()
        finally:
            root.removeHandler(handler)

    def test_http_config_nao_usa_operacoes_financeiras(self):
        import http.client
        from http.server import ThreadingHTTPServer
        from src.interface.servidor import Requisicao, SESSOES, LOCK_SESSOES
        server = ThreadingHTTPServer(('127.0.0.1', 0), Requisicao)
        server.backup_service = BackupService(self.source, self.config, self.credentials)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with LOCK_SESSOES:
            SESSOES['backup-test-session'] = {'id': 1}
        try:
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
            with patch('src.interface.servidor.operacoes.executar') as financial:
                connection.request('POST', '/api/backup/config', json.dumps({'credentials': {'r2_secret_access_key': 'PRIVATE_SENTINEL'}}),
                                   {'Content-Type': 'application/json', 'Cookie': 'sessao=backup-test-session'})
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertNotIn('PRIVATE_SENTINEL', response.read().decode())
                financial.assert_not_called()
            connection.close()
        finally:
            with LOCK_SESSOES:
                SESSOES.pop('backup-test-session', None)
            server.shutdown()
            server.server_close()
            thread.join(2)


if __name__ == '__main__':
    unittest.main()

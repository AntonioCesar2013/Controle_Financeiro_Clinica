import copy
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .config import BackupConfig, atomic_json, validate
from .credentials import CredentialService
from .providers.local import LocalProvider
from .providers.r2 import R2Provider
from .providers.drive import DriveProvider
from .security import protect_sdk_logs


def now():
    return datetime.now(timezone.utc).isoformat()


class BackupService:
    def __init__(self, source, config=None, credentials=None, providers=None):
        protect_sdk_logs()
        self.source = Path(source)
        self.config = config or BackupConfig()
        self.credentials = credentials or CredentialService()
        self.providers = providers or {'local': LocalProvider(), 'r2': R2Provider(self.credentials),
                                      'drive': DriveProvider(self.credentials, self.config)}
        self.lock = threading.Lock()
        self.state_lock = threading.RLock()
        self.status_path = self.config.directory / 'backup-status.json'
        try:
            self.state = json.loads(self.status_path.read_text(encoding='utf-8'))
            if not isinstance(self.state, dict):
                self.state = {}
        except (OSError, ValueError):
            self.state = {}
        if self.state.get('running'):
            self.state['message'] = 'Execução anterior interrompida. Verifique os destinos.'
        self.state['running'] = False
        self.worker = None

    def status(self):
        with self.state_lock:
            result = copy.deepcopy(self.state)
        config = self.config.load()
        result['backup_enabled'] = config['backup_enabled']
        result['interval_hours'] = config['interval_hours']
        if not config['backup_enabled']:
            result['automatic_state'] = 'DESATIVADO'
        elif not result.get('last_success'):
            result['automatic_state'] = 'NUNCA_CONCLUIDO'
        else:
            try:
                last = datetime.fromisoformat(result['last_success'])
                due = last + timedelta(hours=config['interval_hours'])
                result['next_due'] = due.isoformat()
                result['automatic_state'] = 'ATRASADO' if datetime.now(timezone.utc) > due else 'EM_DIA'
            except (TypeError, ValueError):
                result['automatic_state'] = 'NUNCA_CONCLUIDO'
        return result

    def _update(self, **values):
        with self.state_lock:
            self.state.update(copy.deepcopy(values))
            try:
                atomic_json(self.status_path, self.state)
            except OSError:
                self.state['status_warning'] = 'Não foi possível persistir o status em disco.'

    def settings(self):
        try:
            configured, warning = self.credentials.configured(), ''
        except ValueError:
            configured, warning = {}, 'Credential Manager indisponível; instale as dependências e use Windows.'
        return dict(config=self.config.load(), configured=configured, warning=warning, status=self.status())

    def save_settings(self, data):
        config = validate({**self.config.load(), **data.get('config', {})})
        secrets = data.get('credentials', {})
        if not isinstance(secrets, dict) or any(k not in self.credentials.NAMES or k == 'drive_token' for k in secrets):
            raise ValueError('Campos de credenciais inválidos.')
        for key, value in secrets.items():
            if not isinstance(value, str) or len(value) > 2048:
                raise ValueError('Credencial inválida.')
        old = self.config.load()
        if old['drive_client_id'] != config['drive_client_id'] or secrets.get('drive_client_secret'):
            self.credentials.delete_secret('drive_token')
        for key, value in secrets.items():
            if value:
                self.credentials.set_secret(key, value)
        self.config.save(config)
        return self.settings()

    def start(self, action='backup'):
        if action not in ('backup', 'test-r2', 'test-drive', 'connect', 'disconnect'):
            raise ValueError('Ação desconhecida.')
        if not self.lock.acquire(blocking=False):
            self._update(last_skipped=now(), skipped_message='Execução ignorada: operação em andamento.')
            return False
        self._update(running=True, action=action, message='Operação em andamento.')
        self.worker = threading.Thread(target=self._work, args=(action,), name='backup-clinica', daemon=True)
        try:
            self.worker.start()
        except Exception:
            self._update(running=False, message='Não foi possível iniciar a operação.')
            self.lock.release()
            raise
        return True

    def _work(self, action):
        try:
            config = self.config.load()
            if action == 'backup':
                self._backup(config)
            elif action in ('connect', 'disconnect'):
                provider = self.providers['drive']
                provider.connect(config) if action == 'connect' else provider.disconnect()
                self._update(message='Google Drive conectado.' if action == 'connect' else 'Credenciais da conta removidas deste computador.')
            else:
                self.providers[action.removeprefix('test-')].test_connection(config)
                self._update(message='Conexão realizada com sucesso.')
        except Exception:
            # Never expose library exception text: OAuth and SDK exceptions may contain secrets.
            self._update(message='Falha na operação. Verifique configuração, credenciais, acesso à pasta/bucket e conexão. Para Drive, reconecte se o consentimento expirou.')
        finally:
            self._update(running=False)
            self.lock.release()

    def _backup(self, config):
        started = time.monotonic()
        result = dict(snapshot_created=False, integrity_ok=False, local='pending',
                      r2='pending' if config['r2_enabled'] else 'disabled',
                      drive='pending' if config['drive_enabled'] else 'disabled', errors=[])
        self._update(last_attempt=now(), result=result)
        try:
            path = self.providers['local'].upload_backup(self.source, config)
            result.update(snapshot_created=True, integrity_ok=True, local='success', filename=path.name, size=path.stat().st_size)
            self._update(last_success=now(), result=result)
        except Exception:
            result.update(local='failed', r2='skipped' if config['r2_enabled'] else 'disabled',
                          drive='skipped' if config['drive_enabled'] else 'disabled')
            result['errors'].append('Snapshot local falhou: verifique banco, integridade, pasta, permissões e espaço em disco.')
        else:
            for name in ('r2', 'drive'):
                if config[name + '_enabled']:
                    try:
                        self.providers[name].upload_backup(path, config)
                        result[name] = 'success'
                        self._update(**{f'last_{name}_success': now()})
                    except Exception:
                        result[name] = 'failed'
                        result['errors'].append(f'{name}: envio falhou; verifique internet, credenciais e destino. Reconecte o Drive se necessário.')
                    self._update(result=copy.deepcopy(result))
        result['duration_seconds'] = round(time.monotonic() - started, 2)
        self._update(result=result, message='Backup concluído.' if not result['errors'] else
                     ('Backup concluído parcialmente.' if result['local'] == 'success' else 'Backup falhou.'))

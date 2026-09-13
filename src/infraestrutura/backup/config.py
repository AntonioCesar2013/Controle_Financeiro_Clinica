import json
import math
import os
import re
import tempfile
import threading
from pathlib import Path


DEFAULTS = dict(version=1, backup_enabled=False, backup_directory='', interval_hours=6,
                r2_enabled=False, r2_bucket='', r2_endpoint='', r2_prefix='backups/',
                drive_enabled=False, drive_folder_id='', drive_client_id='')


def application_directory():
    from platformdirs import user_data_path
    return user_data_path('Controle_Financeiro_Clinica', appauthor=False, roaming=False)


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def validate(data):
    result = {k: data.get(k, v) for k, v in DEFAULTS.items()}
    for k, default in DEFAULTS.items():
        if isinstance(default, bool) and type(result[k]) is not bool:
            raise ValueError('Ativação inválida.')
        if isinstance(default, str) and (not isinstance(result[k], str) or len(result[k]) > 2048):
            raise ValueError('Configuração textual inválida.')
    value = result['interval_hours']
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0.01 <= value <= 8760:
        raise ValueError('Intervalo deve estar entre 0,01 e 8760 horas.')
    directory = result['backup_directory']
    if directory and not Path(directory).is_absolute():
        raise ValueError('Informe um caminho absoluto para a pasta local.')
    if result['backup_enabled'] and not directory:
        raise ValueError('Escolha a pasta local antes de ativar o backup.')
    endpoint = result['r2_endpoint']
    if endpoint and not re.fullmatch(r'https://[a-fA-F0-9]{32}(?:\.(?:eu|fedramp))?\.r2\.cloudflarestorage\.com', endpoint):
        raise ValueError('Informe o endpoint HTTPS da conta Cloudflare R2, sem barra final.')
    if result['r2_enabled'] and (not endpoint or not result['r2_bucket']):
        raise ValueError('Informe bucket e endpoint do R2.')
    result['version'] = 1
    return result


class BackupConfig:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else application_directory() / 'config'
        self.path = self.directory / 'backup.json'
        self.lock = threading.RLock()

    def load(self):
        with self.lock:
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                return validate(data) if isinstance(data, dict) else dict(DEFAULTS)
            except (OSError, ValueError, TypeError):
                return dict(DEFAULTS)

    def save(self, data):
        with self.lock:
            result = validate({**self.load(), **{k: v for k, v in data.items() if k in DEFAULTS}})
            atomic_json(self.path, result)
            return result

from datetime import datetime
from pathlib import Path
from ..snapshot import create_snapshot


class LocalProvider:
    def upload_backup(self, source, config):
        if not config['backup_directory']:
            raise ValueError('Configure a pasta local de backup.')
        name = f'controle_financeiro_{datetime.now():%Y-%m-%d_%H%M%S_%f}.db'
        return create_snapshot(source, Path(config['backup_directory']) / name)

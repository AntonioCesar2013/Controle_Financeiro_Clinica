from datetime import datetime
from pathlib import Path
from ..snapshot import create_compressed_snapshot


RETENTION_COUNT = 50


class LocalProvider:
    def upload_backup(self, source, config):
        if not config['backup_directory']:
            raise ValueError('Configure a pasta local de backup.')
        directory = Path(config['backup_directory'])
        name = f'controle_financeiro_{datetime.now():%Y-%m-%d_%H%M%S_%f}.db.gz'
        created = create_compressed_snapshot(source, directory / name)
        self._keep_latest(directory, keep=created)
        return created

    @staticmethod
    def _keep_latest(directory, keep):
        """Mantém os 50 backups automáticos mais recentes, incluindo o recém-criado."""
        backups = []
        for pattern in ('controle_financeiro_*.db', 'controle_financeiro_*.db.gz'):
            for path in directory.glob(pattern):
                if path.is_file():
                    backups.append(path)
        backups.sort(key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
        protected = {keep, *backups[:RETENTION_COUNT]}
        for path in backups[RETENTION_COUNT:]:
            if path not in protected:
                path.unlink()

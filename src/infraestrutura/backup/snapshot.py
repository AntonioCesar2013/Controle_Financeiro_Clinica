import os
import sqlite3
import tempfile
import time
from contextlib import closing
from pathlib import Path


def create_snapshot(source, destination):
    source, destination = Path(source), Path(destination)
    if not source.is_file():
        raise FileNotFoundError('Banco de origem inexistente.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=destination.stem, suffix='.tmp', dir=destination.parent)
    os.close(fd)
    deadline = time.monotonic() + 300
    def progress(*_):
        if time.monotonic() > deadline:
            raise TimeoutError('Tempo de snapshot excedido.')
    try:
        with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as origin:
            with closing(sqlite3.connect(temporary)) as target:
                origin.backup(target, pages=256, progress=progress, sleep=0.1)
        with closing(sqlite3.connect(temporary)) as check:
            if check.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Snapshot inválido: verificação de integridade falhou.')
        with open(temporary, 'r+b') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        return destination
    finally:
        Path(temporary).unlink(missing_ok=True)

import gzip
import os
import shutil
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


def create_compressed_snapshot(source, destination):
    """Cria snapshot SQLite íntegro e o publica atomicamente em gzip."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd_db, temporary_db = tempfile.mkstemp(prefix=destination.stem, suffix='.db.tmp', dir=destination.parent)
    os.close(fd_db)
    Path(temporary_db).unlink(missing_ok=True)
    fd_gz, temporary_gz = tempfile.mkstemp(prefix=destination.stem, suffix='.gz.tmp', dir=destination.parent)
    os.close(fd_gz)
    try:
        create_snapshot(source, temporary_db)
        with open(temporary_db, 'rb') as origin, gzip.open(temporary_gz, 'wb', compresslevel=9) as target:
            shutil.copyfileobj(origin, target, length=1024 * 1024)
        with open(temporary_gz, 'r+b') as stream:
            os.fsync(stream.fileno())
        # A leitura completa valida cabeçalho, stream e CRC antes da publicação.
        with gzip.open(temporary_gz, 'rb') as check:
            while check.read(1024 * 1024):
                pass
        os.replace(temporary_gz, destination)
        return destination
    finally:
        Path(temporary_db).unlink(missing_ok=True)
        Path(temporary_gz).unlink(missing_ok=True)


def extract_compressed_snapshot(source, destination):
    """Extrai um .db.gz atomicamente e confirma a integridade SQLite."""
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=destination.stem, suffix='.db.tmp', dir=destination.parent)
    os.close(fd)
    try:
        with gzip.open(source, 'rb') as origin, open(temporary, 'wb') as target:
            shutil.copyfileobj(origin, target, length=1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
        with closing(sqlite3.connect(temporary)) as check:
            if check.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Backup compactado inválido: verificação de integridade falhou.')
        os.replace(temporary, destination)
        return destination
    finally:
        Path(temporary).unlink(missing_ok=True)

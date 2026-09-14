"""Trava entre processos que identifica uma instância usando o banco."""
from pathlib import Path


class BancoEmUsoError(RuntimeError):
    pass


class TravaUsoBanco:
    def __init__(self, caminho_banco):
        self.caminho = Path(str(caminho_banco) + ".uso.lock")
        self.arquivo = None

    def adquirir(self):
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.arquivo = open(self.caminho, "a+b")
            self.arquivo.seek(0)
            if self.arquivo.read(1) == b"":
                self.arquivo.write(b"0")
                self.arquivo.flush()
            self.arquivo.seek(0)
            try:
                import msvcrt
                msvcrt.locking(self.arquivo.fileno(), msvcrt.LK_NBLCK, 1)
            except ImportError:
                import fcntl
                fcntl.flock(self.arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as erro:
            if self.arquivo is not None:
                self.arquivo.close()
            self.arquivo = None
            raise BancoEmUsoError(
                "A restauração foi bloqueada porque existe uma instância do sistema usando o banco. "
                "Feche todas as janelas do sistema e tente novamente."
            ) from erro
        return self

    def liberar(self):
        if self.arquivo is None:
            return
        try:
            self.arquivo.seek(0)
            try:
                import msvcrt
                msvcrt.locking(self.arquivo.fileno(), msvcrt.LK_UNLCK, 1)
            except ImportError:
                import fcntl
                fcntl.flock(self.arquivo.fileno(), fcntl.LOCK_UN)
        finally:
            self.arquivo.close()
            self.arquivo = None

    def __enter__(self):
        return self.adquirir()

    def __exit__(self, *_):
        self.liberar()

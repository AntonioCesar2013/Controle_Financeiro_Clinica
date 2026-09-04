"""Executor pequeno de migrações versionadas no banco único."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable


@dataclass(frozen=True)
class Migracao:
    modulo: str
    versao: int
    aplicar: Callable

    @property
    def identificador(self):
        return f"{self.modulo}:{self.versao}"


def preparar_controle(conexao):
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS migracoes_schema (
            modulo TEXT NOT NULL,
            versao INTEGER NOT NULL,
            aplicada_em TEXT NOT NULL,
            PRIMARY KEY (modulo, versao)
        )
    """)


def aplicar_migracoes(conexao, migracoes: Iterable[Migracao]):
    """Aplica cada migração uma vez dentro da transação do chamador."""
    conexao.execute("SAVEPOINT migracoes_modulo")
    try:
        preparar_controle(conexao)
        aplicadas = {
            (linha[0], linha[1])
            for linha in conexao.execute("SELECT modulo, versao FROM migracoes_schema")
        }
        for migracao in sorted(migracoes, key=lambda item: (item.modulo, item.versao)):
            chave = (migracao.modulo, migracao.versao)
            if chave in aplicadas:
                continue
            migracao.aplicar(conexao)
            conexao.execute(
                "INSERT INTO migracoes_schema(modulo,versao,aplicada_em) VALUES(?,?,?)",
                (*chave, datetime.now(timezone.utc).isoformat()),
            )
        conexao.execute("RELEASE SAVEPOINT migracoes_modulo")
    except Exception:
        conexao.execute("ROLLBACK TO SAVEPOINT migracoes_modulo")
        conexao.execute("RELEASE SAVEPOINT migracoes_modulo")
        raise

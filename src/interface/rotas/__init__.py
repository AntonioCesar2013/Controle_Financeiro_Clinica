"""Registro simples e explícito das rotas HTTP por área."""
from importlib import import_module


GRUPOS = ("sistema", "cadastros", "financeiro", "administracao", "cantina")


def _grupo(nome):
    return import_module(f"src.interface.rotas.{nome}")


def rotas_get(query):
    rotas = {}
    for nome in GRUPOS:
        rotas.update(_grupo(nome).rotas_get(query))
    return rotas


def resolver_rota(rota, query):
    """Importa grupos sob demanda e para assim que encontra a rota solicitada."""
    for nome in GRUPOS:
        funcao = _grupo(nome).rotas_get(query).get(rota)
        if funcao is not None:
            return funcao
    return None

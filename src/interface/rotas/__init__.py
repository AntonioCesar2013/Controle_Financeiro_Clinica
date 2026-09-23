"""Registro simples e explícito das rotas HTTP por área."""

from src.interface.rotas import administracao, cadastros, cantina, financeiro, sistema


def rotas_get(query):
    rotas = {}
    for grupo in (sistema, cadastros, financeiro, administracao, cantina):
        rotas.update(grupo.rotas_get(query))
    return rotas

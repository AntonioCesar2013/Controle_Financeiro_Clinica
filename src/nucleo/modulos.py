"""Registro explícito dos módulos que compõem a aplicação única."""

from dataclasses import dataclass
from importlib import import_module
from typing import Callable, Iterable


@dataclass(frozen=True)
class Modulo:
    nome: str
    preparar_banco: Callable
    permissoes: tuple[str, ...] = ()


_CAMINHOS = (
    "src.cadastros.modulo",
    "src.financeiro.modulo",
    "src.cantina.modulo",
)


def modulos_registrados() -> tuple[Modulo, ...]:
    """Retorna os módulos em ordem estável de inicialização."""
    return tuple(import_module(caminho).MODULO for caminho in _CAMINHOS)


def preparar_modulos(conexao, modulos: Iterable[Modulo] | None = None):
    for modulo in modulos or modulos_registrados():
        modulo.preparar_banco(conexao)


def permissoes_disponiveis() -> tuple[str, ...]:
    """Ponto de extensão; ainda não bloqueia nenhuma operação."""
    return tuple(
        permissao
        for modulo in modulos_registrados()
        for permissao in modulo.permissoes
    )

"""Entrada compatível. Implementação em src.infraestrutura.backup_banco."""

import importlib
import runpy
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    runpy.run_module("src.infraestrutura.backup_banco", run_name="__main__")
else:
    # Usa o mesmo módulo, inclusive ao configurar o caminho do banco em testes.
    sys.modules[__name__] = importlib.import_module("src.infraestrutura.backup_banco")

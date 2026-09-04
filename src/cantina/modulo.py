from src.nucleo.migracoes import Migracao, aplicar_migracoes
from src.nucleo.modulos import Modulo


def _validar_schema(conexao):
    for tabela in ("itens", "carteiras", "vendas_cantina", "movimentacoes_estoque"):
        if not conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)
        ).fetchone():
            raise RuntimeError(f"Tabela da Cantina ausente: {tabela}")


def preparar_banco(conexao):
    aplicar_migracoes(conexao, (Migracao("cantina", 1, _validar_schema),))


MODULO = Modulo(
    "cantina",
    preparar_banco,
    ("cantina.visualizar", "cantina.vender", "cantina.ajustar_estoque", "cantina.estornar"),
)

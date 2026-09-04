from src.nucleo.migracoes import Migracao, aplicar_migracoes
from src.nucleo.modulos import Modulo


def _validar_schema(conexao):
    for tabela in ("cobrancas", "recebimentos", "contas_pagar", "pagamentos_saida"):
        if not conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)
        ).fetchone():
            raise RuntimeError(f"Tabela financeira ausente: {tabela}")


def _adicionar_desconto_contas_pagar(conexao):
    colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(contas_pagar)")}
    if "desconto" not in colunas:
        conexao.execute("ALTER TABLE contas_pagar ADD COLUMN desconto INTEGER NOT NULL DEFAULT 0")


def preparar_banco(conexao):
    aplicar_migracoes(conexao, (
        Migracao("financeiro", 1, _validar_schema),
        Migracao("financeiro", 2, _adicionar_desconto_contas_pagar),
    ))


MODULO = Modulo(
    "financeiro",
    preparar_banco,
    ("financeiro.visualizar", "financeiro.receber", "financeiro.pagar", "financeiro.estornar"),
)

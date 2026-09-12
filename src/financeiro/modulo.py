from src.nucleo.migracoes import Migracao, aplicar_migracoes
from src.nucleo.modulos import Modulo
from src.financeiro.migracao_conferencia import aplicar as preparar_conferencia
from src.financeiro.migracao_fluxos import aplicar as preparar_fluxos
from src.financeiro.migracao_estornos_devolucoes import aplicar as preparar_estornos_devolucoes


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


def _adicionar_multa_juros(conexao):
    for tabela in ("recebimentos", "pagamentos_saida"):
        colunas = {linha[1] for linha in conexao.execute(f"PRAGMA table_info({tabela})")}
        if "multa_juros" not in colunas:
            conexao.execute(
                f"ALTER TABLE {tabela} ADD COLUMN multa_juros INTEGER NOT NULL DEFAULT 0"
            )

    # O valor adicional também faz parte de um recebimento conciliado.
    conexao.execute("DROP TRIGGER IF EXISTS proteger_conciliado_recebimentos_update")
    conexao.execute("""CREATE TRIGGER proteger_conciliado_recebimentos_update
        BEFORE UPDATE OF valor,multa_juros,data_recebimento,cobranca_id ON recebimentos
        WHEN EXISTS(SELECT 1 FROM conciliacoes_vinculos WHERE recebimento_id=OLD.id)
        BEGIN SELECT RAISE(ABORT, 'Desfaça a conciliação bancária antes de alterar este lançamento.'); END""")


def _adicionar_desconto_movimentacoes(conexao):
    for tabela in ("recebimentos", "pagamentos_saida"):
        colunas = {linha[1] for linha in conexao.execute(f"PRAGMA table_info({tabela})")}
        if "desconto" not in colunas:
            conexao.execute(
                f"ALTER TABLE {tabela} ADD COLUMN desconto INTEGER NOT NULL DEFAULT 0"
            )
    conexao.execute("DROP TRIGGER IF EXISTS proteger_conciliado_recebimentos_update")
    conexao.execute("""CREATE TRIGGER proteger_conciliado_recebimentos_update
        BEFORE UPDATE OF valor,desconto,multa_juros,data_recebimento,cobranca_id ON recebimentos
        WHEN EXISTS(SELECT 1 FROM conciliacoes_vinculos WHERE recebimento_id=OLD.id)
        BEGIN SELECT RAISE(ABORT, 'Desfaça a conciliação bancária antes de alterar este lançamento.'); END""")


def preparar_banco(conexao):
    aplicar_migracoes(conexao, (
        Migracao("financeiro", 1, _validar_schema),
        Migracao("financeiro", 2, _adicionar_desconto_contas_pagar),
        Migracao("financeiro", 3, preparar_conferencia),
        Migracao("financeiro", 4, _adicionar_multa_juros),
        Migracao("financeiro", 5, _adicionar_desconto_movimentacoes),
        Migracao("financeiro", 6, preparar_fluxos),
        Migracao("financeiro", 7, preparar_estornos_devolucoes),
    ))


MODULO = Modulo(
    "financeiro",
    preparar_banco,
    ("financeiro.visualizar", "financeiro.receber", "financeiro.pagar", "financeiro.estornar"),
)

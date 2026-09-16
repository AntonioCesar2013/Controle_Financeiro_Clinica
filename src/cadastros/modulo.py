from src.nucleo.migracoes import Migracao, aplicar_migracoes
from src.nucleo.modulos import Modulo
from src.cadastros.contatos import preparar_schema


def _validar_schema(conexao):
    # O bootstrap compatível cria estas tabelas antes da primeira migração modular.
    for tabela in ("residentes", "responsaveis", "colaboradores", "internacoes"):
        if not conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)
        ).fetchone():
            raise RuntimeError(f"Tabela compartilhada ausente: {tabela}")


def _preparar_itens_residentes(conexao):
    conexao.execute("""CREATE TABLE IF NOT EXISTS itens_residentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        residente_id INTEGER NOT NULL REFERENCES residentes(id) ON DELETE RESTRICT,
        nome TEXT NOT NULL CHECK (LENGTH(TRIM(nome)) > 0),
        quantidade INTEGER NOT NULL DEFAULT 1 CHECK (quantidade > 0),
        descricao TEXT,
        cadastrado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_itens_residentes_residente ON itens_residentes(residente_id,id)")


def _datas_itens_residentes(conexao):
    # Registros antigos ficam sem data de entrada: cadastro não comprova a entrega real.
    colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(itens_residentes)")}
    if "data_entrada" not in colunas:
        conexao.execute("ALTER TABLE itens_residentes ADD COLUMN data_entrada TEXT")
    if "data_retirada" not in colunas:
        conexao.execute("ALTER TABLE itens_residentes ADD COLUMN data_retirada TEXT")


def preparar_banco(conexao):
    aplicar_migracoes(conexao, (
        Migracao("cadastros", 1, _validar_schema),
        Migracao("cadastros", 2, preparar_schema),
        Migracao("cadastros", 3, _preparar_itens_residentes),
        Migracao("cadastros", 4, _datas_itens_residentes),
    ))


MODULO = Modulo("cadastros", preparar_banco)

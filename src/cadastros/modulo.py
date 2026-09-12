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


def preparar_banco(conexao):
    aplicar_migracoes(conexao, (Migracao("cadastros", 1, _validar_schema), Migracao("cadastros", 2, preparar_schema)))


MODULO = Modulo("cadastros", preparar_banco)

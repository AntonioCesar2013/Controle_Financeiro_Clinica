"""Migração dos nomes genéricos das tabelas de produtos da Cantina."""


RENOMEACOES = (
    ("itens", "itens_cantina"),
    ("itens_valores", "itens_cantina_valores"),
    ("vendas_cantina_itens", "vendas_cantina_itens_cantina"),
)


def migrar(conexao):
    """Renomeia tabelas legadas sem copiar ou recriar seus registros."""
    tabelas = {
        linha[0]
        for linha in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    for nome_antigo, nome_novo in RENOMEACOES:
        antigo_existe = nome_antigo in tabelas
        novo_existe = nome_novo in tabelas
        if antigo_existe and novo_existe:
            raise RuntimeError(
                f"Não foi possível migrar a Cantina: as tabelas {nome_antigo} "
                f"e {nome_novo} coexistem."
            )
        if antigo_existe:
            conexao.execute(f'ALTER TABLE "{nome_antigo}" RENAME TO "{nome_novo}"')
            tabelas.remove(nome_antigo)
            tabelas.add(nome_novo)

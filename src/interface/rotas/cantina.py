from src.cantina import produtos, vendas
from src.interface.consultas_interface import listar_carteiras


def _parametro(query, nome, padrao=None):
    valores = query.get(nome)
    return valores[0] if valores else padrao


def rotas_get(query):
    return {
        "/api/carteiras": listar_carteiras,
        "/api/carteiras/detalhe": lambda: vendas.consultar_carteira(_parametro(query, "id")),
        "/api/cantina": vendas.consultar_cantina,
        "/api/cantina/produto": lambda: vendas.buscar_produto_codigo(
            _parametro(query, "codigo"), _parametro(query, "data")
        ),
        "/api/itens": lambda: produtos.listar_itens(apenas_ativos=False),
        "/api/itens/historico": lambda: {
            "precos": produtos.listar_valores_item(_parametro(query, "id"), apenas_ativos=False),
            "estoque": produtos.listar_movimentacoes_estoque(_parametro(query, "id")),
        },
    }

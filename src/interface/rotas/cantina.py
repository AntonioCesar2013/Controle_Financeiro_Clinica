from src.cantina import produtos, vendas
from src.interface.consultas_interface import listar_carteiras


def _parametro(query, nome, padrao=None):
    valores = query.get(nome)
    return valores[0] if valores else padrao


def rotas_get(query):
    return {
        "/api/carteiras": listar_carteiras,
        "/api/carteiras/detalhe": lambda: vendas.consultar_carteira(
            _parametro(query, "id"), _parametro(query, "pagina", 1), _parametro(query, "tamanho", 50)),
        "/api/cantina": lambda: vendas.consultar_cantina(
            _parametro(query, "pagina", 1), _parametro(query, "tamanho", 50)),
        "/api/itens": lambda: produtos.listar_itens(apenas_ativos=False),
        "/api/itens/historico": lambda: produtos.historico_item_paginado(
            _parametro(query, "id"), _parametro(query, "pagina", 1), _parametro(query, "tamanho", 50)),
    }

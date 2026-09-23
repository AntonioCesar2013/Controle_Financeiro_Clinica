from src.administracao import itens


def _p(query,nome,padrao=None):
    valores=query.get(nome); return valores[0] if valores else padrao


def rotas_get(query):
    return {
        "/api/administracao/itens": lambda: itens.listar(
            _p(query,"busca"),_p(query,"setor_id"),_p(query,"categoria"),_p(query,"estado_conservacao"),
            _p(query,"ativo"),_p(query,"pagina",1),_p(query,"tamanho",50),_p(query,"ordem","nome_asc")),
        "/api/administracao/itens/detalhe": lambda: itens.detalhe(_p(query,"id")),
        "/api/administracao/itens/historico": lambda: itens.historico(_p(query,"id"),_p(query,"pagina",1),_p(query,"tamanho",50)),
    }

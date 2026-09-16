from src.cadastros import convenios
from src.cadastros import itens_residentes
from src.cadastros.internacoes import buscar_internacao
from src.interface import extrato_residente
from src.interface.consultas_interface import (
    listar_internacoes,
    listar_residentes,
    listar_responsaveis,
)


def _parametro(query, nome, padrao=None):
    valores = query.get(nome)
    return valores[0] if valores else padrao


def rotas_get(query):
    inicio = _parametro(query, "data_inicio")
    fim = _parametro(query, "data_fim")
    return {
        "/api/residentes": listar_residentes,
        "/api/residentes/itens": lambda: itens_residentes.listar(_parametro(query, "residente_id")),
        "/api/residentes/extrato": lambda: extrato_residente.consultar(
            _parametro(query, "id"), inicio, fim
        ),
        "/api/responsaveis": listar_responsaveis,
        "/api/internacoes": listar_internacoes,
        "/api/internacoes/detalhe": lambda: buscar_internacao(_parametro(query, "id")),
        "/api/convenios": lambda: convenios.listar_convenios(False),
    }

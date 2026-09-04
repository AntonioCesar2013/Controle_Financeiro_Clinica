from src.infraestrutura import auditoria, sincronizacao_nuvem
from src.interface import relatorios
from src.interface.consultas_interface import listar_colaboradores


def _parametro(query, nome, padrao=None):
    valores = query.get(nome)
    return valores[0] if valores else padrao


def rotas_get(query):
    inicio = _parametro(query, "data_inicio")
    fim = _parametro(query, "data_fim")
    return {
        "/api/colaboradores": listar_colaboradores,
        "/api/sincronizacao/status": sincronizacao_nuvem.obter_status,
        "/api/relatorios": lambda: relatorios.gerar(
            _parametro(query, "tipo", "financeiro"), inicio, fim
        ),
        "/api/auditoria": lambda: auditoria.listar(_parametro(query, "limite", 500)),
    }

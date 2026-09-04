from datetime import date

from src.financeiro import (
    caixa,
    configuracoes_financeiras,
    contas_pagar,
    contas_receber,
    despesas,
    pagamentos,
    recebimentos,
    recibos,
)
from src.financeiro.estornos import historico, historico_ajustes


def _parametro(query, nome, padrao=None):
    valores = query.get(nome)
    return valores[0] if valores else padrao


def rotas_get(query):
    inicio = _parametro(query, "data_inicio")
    fim = _parametro(query, "data_fim")
    return {
        "/api/recibos": lambda: recibos.consultar(_parametro(query, "id")),
        "/api/contas-receber": lambda: contas_receber.listar_cobrancas_consolidadas(
            data_referencia=date.today().isoformat()
        ),
        "/api/contas-receber/detalhe": lambda: contas_receber.buscar_cobranca_consolidada(
            _parametro(query, "id"), data_referencia=date.today().isoformat()
        ),
        "/api/mensalidades": lambda: contas_receber.listar_mensalidades(
            data_referencia=date.today().isoformat()
        ),
        "/api/contas-pagar": lambda: contas_pagar.listar_contas(
            status=_parametro(query, "status"), data_inicio=inicio, data_fim=fim
        ),
        "/api/contas-pagar/detalhe": lambda: {
            **contas_pagar.buscar_conta(_parametro(query, "id")),
            **contas_pagar.calcular_total_pago(_parametro(query, "id")),
        },
        "/api/caixa": lambda: {
            **caixa.resumo_caixa(inicio, fim),
            "movimentacoes": caixa.listar_movimentacoes(inicio, fim),
        },
        "/api/despesas": lambda: despesas.listar_despesas(apenas_ativas=False),
        "/api/financeiro/cadastros": lambda: {
            "setores": despesas.listar_setores(False),
            "despesas": despesas.listar_despesas(False),
        },
        "/api/contas-pagar/pagamentos": lambda: historico(
            "pagamentos_saida",
            _parametro(query, "id"),
            pagamentos.listar_pagamentos(_parametro(query, "id")),
        ),
        "/api/contas-receber/recebimentos": lambda: historico(
            "recebimentos",
            _parametro(query, "id"),
            recebimentos.buscar_pagamentos(_parametro(query, "id")),
        ),
        "/api/cobrancas/ajustes": lambda: historico_ajustes(_parametro(query, "id")),
        "/api/configuracoes": configuracoes_financeiras.obter_configuracao,
    }

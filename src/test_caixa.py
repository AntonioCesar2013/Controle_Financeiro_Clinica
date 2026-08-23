"""Teste de consulta do fluxo de caixa; não insere, altera ou exclui dados."""

from datetime import date

from src import caixa


def _imprimir(nome, resultado):
    print(f"\n=== {nome} ===")
    print(resultado)


def testar_caixa():
    hoje = date.today().isoformat()
    ano_atual = date.today().year

    movimentacoes = caixa.listar_movimentacoes()
    _imprimir("1. LISTAR MOVIMENTAÇÕES", movimentacoes)
    assert all(m["tipo"] in ("ENTRADA", "SAIDA") for m in movimentacoes)
    assert all(
        {"id", "data", "tipo", "descricao", "valor", "forma_pagamento", "origem_id"}
        <= set(movimentacao)
        for movimentacao in movimentacoes
    )

    geral = caixa.resumo_caixa()
    _imprimir("2. RESUMO GERAL", geral)
    assert geral["resultado"] == geral["total_entradas"] - geral["total_saidas"]

    diario = caixa.resumo_diario(hoje)
    _imprimir("3. RESUMO DIÁRIO", diario)
    assert diario["data_inicio"] == diario["data_fim"] == hoje

    semanal = caixa.resumo_semanal(hoje)
    _imprimir("4. RESUMO SEMANAL", semanal)
    assert semanal["data_inicio"] <= hoje <= semanal["data_fim"]
    assert semanal["data_inicio"] < semanal["data_fim"]

    mensal = caixa.resumo_mensal(ano_atual, date.today().month)
    _imprimir("5. RESUMO MENSAL", mensal)

    anual = caixa.resumo_anual(ano_atual)
    _imprimir("6. RESUMO ANUAL", anual)

    periodo = caixa.resumo_periodo(hoje, hoje)
    _imprimir("7. PERÍODO PERSONALIZADO", periodo)
    assert periodo == caixa.resumo_caixa(hoje, hoje)

    saldo = caixa.saldo_acumulado(hoje)
    _imprimir("8. SALDO ACUMULADO", saldo)
    assert saldo == caixa.resumo_caixa(data_fim=hoje)["resultado"]

    mensal_detalhado = caixa.resumo_mensal_detalhado(ano_atual, date.today().month)
    _imprimir("9. RESUMO MENSAL DETALHADO", mensal_detalhado)
    assert mensal_detalhado[0]["data"].endswith("-01")

    anual_detalhado = caixa.resumo_anual_detalhado(ano_atual)
    _imprimir("10. RESUMO ANUAL DETALHADO", anual_detalhado)
    assert len(anual_detalhado) == 12

    sem_movimentacoes = caixa.resumo_periodo("1900-01-01", "1900-01-01")
    _imprimir("11. PERÍODO SEM MOVIMENTAÇÕES", sem_movimentacoes)
    assert sem_movimentacoes["total_entradas"] == 0
    assert sem_movimentacoes["total_saidas"] == 0
    print("\n=== TESTE DE CAIXA FINALIZADO COM SUCESSO ===")


if __name__ == "__main__":
    testar_caixa()

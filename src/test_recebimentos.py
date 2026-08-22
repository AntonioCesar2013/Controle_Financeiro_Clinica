"""Teste manual do fluxo de recebimentos usando apenas as APIs públicas."""

from src import recebimentos
from src.cobrancas import listar_cobrancas
from src.internacoes import buscar_internacao


def _funcoes_necessarias_disponiveis():
    faltantes = []

    if not hasattr(recebimentos, "buscar_recebimento"):
        faltantes.append("buscar_recebimento(recebimento_id)")

    if not hasattr(recebimentos, "excluir_recebimento"):
        faltantes.append("excluir_recebimento(recebimento_id)")

    if faltantes:
        print("=== TESTE DE RECEBIMENTOS ===")
        print("Teste não executado para não alterar dados sem poder restaurá-los.")
        print("Funções necessárias ausentes em src.recebimentos:")
        for funcao in faltantes:
            print(f"- {funcao}")
        print("=== TESTE FINALIZADO ===")
        return False

    return True


def _listar_cobrancas_abertas():
    cobrancas_abertas = []

    for internacao_id in range(1, 1000):
        internacao = buscar_internacao(internacao_id)
        if internacao is None:
            continue

        for cobranca in listar_cobrancas(internacao_id):
            if cobranca["status"] == "ABERTA":
                cobrancas_abertas.append(cobranca)

    return cobrancas_abertas


def testar_recebimentos():
    if not _funcoes_necessarias_disponiveis():
        return

    print("=== TESTE DE RECEBIMENTOS ===")
    cobrancas_abertas = _listar_cobrancas_abertas()
    print("Cobranças disponíveis:")
    for cobranca in cobrancas_abertas:
        print(cobranca)

    if not cobrancas_abertas:
        print("Nenhuma cobrança ABERTA disponível para teste.")
        print("=== TESTE FINALIZADO ===")
        return

    cobranca = cobrancas_abertas[0]
    cobranca_id = cobranca["id"]
    print(f"Cobrança escolhida: {cobranca_id}")

    resumo_inicial = recebimentos.resumo_cobranca(cobranca_id)
    print("Resumo inicial:", resumo_inicial)

    parcial = max(1, resumo_inicial["restante"] // 2)
    primeiro = recebimentos.registrar_pagamento(
        cobranca_id, "2026-10-01", parcial, "PIX", "Teste parcial"
    )
    print("Recebimento parcial:", primeiro)
    print("Resumo após parcial:", recebimentos.resumo_cobranca(cobranca_id))

    restante = recebimentos.resumo_cobranca(cobranca_id)["restante"]
    segundo = recebimentos.registrar_pagamento(
        cobranca_id, "2026-10-02", restante, "DINHEIRO", "Quitação de teste"
    )
    print("Quitação:", segundo)
    print("Resumo final:", recebimentos.resumo_cobranca(cobranca_id))

    registros = recebimentos.buscar_pagamentos(cobranca_id)
    print("Recebimentos:", registros)
    print("Recebimento específico:", recebimentos.buscar_recebimento(primeiro["id"]))

    excedente = recebimentos.registrar_pagamento(
        cobranca_id, "2026-10-03", 1, "PIX", "Teste excedente"
    )
    print("Recebimento excedente:", excedente)

    zero = recebimentos.registrar_pagamento(
        cobranca_id, "2026-10-03", 0, "PIX", "Teste zero"
    )
    print("Recebimento zero:", zero)

    inexistente = recebimentos.registrar_pagamento(
        999999, "2026-10-03", 100, "PIX", "Teste inexistente"
    )
    print("Cobrança inexistente:", inexistente)

    exclusao = recebimentos.excluir_recebimento(primeiro["id"])
    print("Exclusão:", exclusao)
    print("Resumo após exclusão:", recebimentos.resumo_cobranca(cobranca_id))
    print("Recebimentos restantes:", recebimentos.buscar_pagamentos(cobranca_id))
    print("=== TESTE FINALIZADO ===")


if __name__ == "__main__":
    testar_recebimentos()

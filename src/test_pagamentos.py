from src.contas_pagar import listar_contas
from src.pagamentos import (
    registrar_pagamento,
    resumo_conta,
    listar_pagamentos,
    buscar_pagamento,
    excluir_pagamento,
)


print("=== TESTE DE PAGAMENTOS ===")


# ============================================================
# 1. CONTAS DISPONÍVEIS
# ============================================================

print("\n=== 1. CONTAS DISPONÍVEIS ===")

contas = listar_contas()

if not contas:
    print("Nenhuma conta encontrada.")
    print("Execute primeiro:")
    print("python -m src.test_contas_pagar")
    raise SystemExit

for conta in contas:
    print(conta)


# ============================================================
# 2. ESCOLHENDO UMA CONTA ABERTA
# ============================================================

conta = next(
    (c for c in contas if c["status"] == "ABERTA"),
    None
)

if not conta:
    print("\nNenhuma conta ABERTA disponível para teste.")
    raise SystemExit

conta_id = conta["id"]
valor_conta = conta["valor"]

print(f"\nConta escolhida para teste: ID {conta_id}")
print(f"Valor da conta: R$ {valor_conta / 100:.2f}")


# ============================================================
# 3. RESUMO INICIAL
# ============================================================

print("\n=== 3. RESUMO INICIAL DA CONTA ===")

resultado = resumo_conta(conta_id)
print(resultado)


# ============================================================
# 4. PAGAMENTO PARCIAL
# ============================================================

print("\n=== 4. REGISTRANDO PAGAMENTO PARCIAL ===")

# Paga aproximadamente 40% da conta
valor_parcial = valor_conta * 40 // 100

resultado = registrar_pagamento(
    conta_pagar_id=conta_id,
    data_pagamento="2026-09-10",
    valor=valor_parcial,
    forma_pagamento="PIX",
    observacao="Primeira parte do pagamento"
)

print(resultado)


# ============================================================
# 5. RESUMO APÓS PAGAMENTO PARCIAL
# ============================================================

print("\n=== 5. RESUMO APÓS PAGAMENTO PARCIAL ===")

resultado = resumo_conta(conta_id)
print(resultado)


# ============================================================
# 6. SEGUNDO PAGAMENTO
# ============================================================

print("\n=== 6. REGISTRANDO SEGUNDO PAGAMENTO ===")

resumo = resumo_conta(conta_id)

if resumo["sucesso"] and resumo["restante"] > 0:

    restante = resumo["restante"]

    resultado = registrar_pagamento(
        conta_pagar_id=conta_id,
        data_pagamento="2026-09-12",
        valor=restante,
        forma_pagamento="DINHEIRO",
        observacao="Quitação da conta"
    )

    print(resultado)


# ============================================================
# 7. RESUMO FINAL
# ============================================================

print("\n=== 7. RESUMO FINAL DA CONTA ===")

resultado = resumo_conta(conta_id)
print(resultado)


# ============================================================
# 8. LISTANDO PAGAMENTOS
# ============================================================

print("\n=== 8. PAGAMENTOS DA CONTA ===")

pagamentos = listar_pagamentos(conta_id)

for pagamento in pagamentos:
    print(pagamento)


# ============================================================
# 9. BUSCANDO UM PAGAMENTO
# ============================================================

if pagamentos:

    pagamento_id = pagamentos[0]["id"]

    print(
        f"\n=== 9. BUSCANDO PAGAMENTO ID {pagamento_id} ==="
    )

    resultado = buscar_pagamento(pagamento_id)
    print(resultado)


# ============================================================
# 10. TENTANDO PAGAR ALÉM DO VALOR
# ============================================================

print("\n=== 10. TENTANDO PAGAR ALÉM DO VALOR ===")

resultado = registrar_pagamento(
    conta_pagar_id=conta_id,
    data_pagamento="2026-09-15",
    valor=1,
    forma_pagamento="PIX",
    observacao="Teste de pagamento excedente"
)

print(resultado)


# ============================================================
# 11. TESTANDO CONTA INEXISTENTE
# ============================================================

print("\n=== 11. TESTANDO CONTA INEXISTENTE ===")

resultado = registrar_pagamento(
    conta_pagar_id=999999,
    data_pagamento="2026-09-20",
    valor=1000,
    forma_pagamento="PIX",
    observacao="Teste de conta inexistente"
)

print(resultado)


# ============================================================
# 12. TESTANDO VALOR INVÁLIDO
# ============================================================

print("\n=== 12. TESTANDO VALOR INVÁLIDO ===")

resultado = registrar_pagamento(
    conta_pagar_id=conta_id,
    data_pagamento="2026-09-20",
    valor=0,
    forma_pagamento="PIX",
    observacao="Teste de valor inválido"
)

print(resultado)


# ============================================================
# 13. TESTANDO DATA INVÁLIDA
# ============================================================

print("\n=== 13. TESTANDO DATA INVÁLIDA ===")

resultado = registrar_pagamento(
    conta_pagar_id=conta_id,
    data_pagamento="20/09/2026",
    valor=1000,
    forma_pagamento="PIX",
    observacao="Teste de data inválida"
)

print(resultado)


# ============================================================
# 14. EXCLUINDO UM PAGAMENTO
# ============================================================

pagamentos = listar_pagamentos(conta_id)

if pagamentos:

    pagamento_id = pagamentos[0]["id"]

    print(
        f"\n=== 14. EXCLUINDO PAGAMENTO ID {pagamento_id} ==="
    )

    resultado = excluir_pagamento(pagamento_id)
    print(resultado)


# ============================================================
# 15. RESUMO APÓS EXCLUSÃO
# ============================================================

print("\n=== 15. RESUMO APÓS EXCLUSÃO ===")

resultado = resumo_conta(conta_id)
print(resultado)


# ============================================================
# 16. PAGAMENTOS RESTANTES
# ============================================================

print("\n=== 16. PAGAMENTOS RESTANTES ===")

pagamentos = listar_pagamentos(conta_id)

for pagamento in pagamentos:
    print(pagamento)


print("\n=== TESTE FINALIZADO ===")

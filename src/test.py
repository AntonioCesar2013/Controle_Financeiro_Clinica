from src.cobrancas import (
    aplicar_desconto,
    listar_cobrancas
)


print("=== TESTE DE DESCONTOS ===")


# ============================================================
# 1. LOCALIZAR UMA COBRANÇA DE MENSALIDADE
# ============================================================

print("\n=== 1. LOCALIZANDO COBRANÇA ===")

cobrancas = listar_cobrancas(1)

cobranca_parcial = None
cobranca_total = None

for cobranca in cobrancas:
    if cobranca["tipo"] == "MENSALIDADE":
        if cobranca_parcial is None:
            cobranca_parcial = cobranca
        elif cobranca_total is None:
            cobranca_total = cobranca


if cobranca_parcial is None:
    print("Nenhuma cobrança de mensalidade encontrada.")
    raise SystemExit


print("Cobrança para teste parcial:")
print(cobranca_parcial)


# ============================================================
# 2. DESCONTO PARCIAL
# ============================================================

print("\n=== 2. APLICANDO DESCONTO PARCIAL ===")

resultado = aplicar_desconto(
    cobranca_parcial["id"],
    500
)

print(resultado)


# ============================================================
# 3. CONSULTANDO A COBRANÇA
# ============================================================

print("\n=== 3. COBRANÇA APÓS DESCONTO ===")

cobrancas = listar_cobrancas(1)

for cobranca in cobrancas:
    if cobranca["id"] == cobranca_parcial["id"]:
        print(cobranca)


# ============================================================
# 4. TENTANDO APLICAR DESCONTO ACIMA DO VALOR RESTANTE
# ============================================================

print("\n=== 4. TESTANDO DESCONTO ACIMA DO LIMITE ===")

resultado = aplicar_desconto(
    cobranca_parcial["id"],
    3000
)

print(resultado)


# ============================================================
# 5. TESTANDO DESCONTO TOTAL
# ============================================================

if cobranca_total is not None:

    print("\n=== 5. APLICANDO DESCONTO TOTAL ===")

    print("Cobrança escolhida:")
    print(cobranca_total)

    resultado = aplicar_desconto(
        cobranca_total["id"],
        cobranca_total["valor"]
    )

    print(resultado)


    # ========================================================
    # 6. CONSULTANDO COBRANÇA DESCONTADA
    # ========================================================

    print("\n=== 6. COBRANÇA APÓS DESCONTO TOTAL ===")

    cobrancas = listar_cobrancas(1)

    for cobranca in cobrancas:
        if cobranca["id"] == cobranca_total["id"]:
            print(cobranca)


    # ========================================================
    # 7. TENTANDO APLICAR OUTRO DESCONTO
    # ========================================================

    print("\n=== 7. TENTANDO DESCONTAR NOVAMENTE ===")

    resultado = aplicar_desconto(
        cobranca_total["id"],
        100
    )

    print(resultado)

else:
    print("\nNão foi encontrada uma segunda mensalidade para o teste total.")


print("\n=== TESTES FINALIZADOS ===")
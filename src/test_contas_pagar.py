from src.contas_pagar import (
    cadastrar_conta,
    buscar_conta,
    listar_contas,
    calcular_total_pago,
    atualizar_status_conta,
    cancelar_conta,
)


print("=== TESTE DE CONTAS A PAGAR ===")


# ============================================================
# 1. LOCALIZANDO DESPESAS EXISTENTES
# ============================================================

print("\n=== 1. DESPESAS DISPONÍVEIS ===")

import sqlite3

conexao = sqlite3.connect("dados/clinica.db")
cursor = conexao.cursor()

cursor.execute("""
    SELECT
        d.id,
        d.descricao,
        s.nome,
        t.nome
    FROM despesas d
    INNER JOIN setores s
        ON s.id = d.setor_id
    INNER JOIN tipos_despesa t
        ON t.id = d.tipo_despesa_id
    WHERE d.ativo = 1
    ORDER BY d.id
""")

despesas = cursor.fetchall()

for despesa in despesas:
    print({
        "id": despesa[0],
        "descricao": despesa[1],
        "setor": despesa[2],
        "tipo": despesa[3],
    })

conexao.close()


if not despesas:
    print("\nNenhuma despesa encontrada.")
    print("Execute primeiro:")
    print("python -m src.test_despesas")
    raise SystemExit


# ============================================================
# 2. PEGANDO ALGUMAS DESPESAS PARA TESTE
# ============================================================

despesa_internet = None
despesa_alimentacao = None
despesa_combustivel = None
despesa_manutencao = None

for despesa in despesas:

    descricao = despesa[1].lower()

    if "internet" in descricao:
        despesa_internet = despesa[0]

    elif "alimentos" in descricao:
        despesa_alimentacao = despesa[0]

    elif "combust" in descricao:
        despesa_combustivel = despesa[0]

    elif "reparos" in descricao:
        despesa_manutencao = despesa[0]


# ============================================================
# 3. CADASTRANDO CONTAS
# ============================================================

print("\n=== 2. CADASTRANDO CONTAS ===")

ids_contas = []


# Internet
if despesa_internet:

    resultado = cadastrar_conta(
        despesa_id=despesa_internet,
        data_vencimento="2026-09-10",
        valor=18000,
    )

    print("Internet:")
    print(resultado)

    if resultado["sucesso"]:
        ids_contas.append(resultado["id"])


# Alimentação
if despesa_alimentacao:

    resultado = cadastrar_conta(
        despesa_id=despesa_alimentacao,
        data_vencimento="2026-09-05",
        valor=125000,
    )

    print("Alimentação:")
    print(resultado)

    if resultado["sucesso"]:
        ids_contas.append(resultado["id"])


# Combustível
if despesa_combustivel:

    resultado = cadastrar_conta(
        despesa_id=despesa_combustivel,
        data_vencimento="2026-09-08",
        valor=85000,
    )

    print("Combustível:")
    print(resultado)

    if resultado["sucesso"]:
        ids_contas.append(resultado["id"])


# Manutenção extraordinária
if despesa_manutencao:

    resultado = cadastrar_conta(
        despesa_id=despesa_manutencao,
        data_vencimento="2026-09-15",
        valor=230000,
    )

    print("Manutenção:")
    print(resultado)

    if resultado["sucesso"]:
        ids_contas.append(resultado["id"])


# ============================================================
# 4. LISTANDO CONTAS
# ============================================================

print("\n=== 3. LISTANDO TODAS AS CONTAS ===")

for conta in listar_contas():
    print(conta)


# ============================================================
# 5. BUSCANDO UMA CONTA
# ============================================================

print("\n=== 4. BUSCANDO UMA CONTA ===")

if ids_contas:

    conta_id = ids_contas[0]

    resultado = buscar_conta(conta_id)

    print(resultado)


# ============================================================
# 6. RESUMO DA CONTA
# ============================================================

print("\n=== 5. RESUMO DA CONTA ===")

if ids_contas:

    conta_id = ids_contas[0]

    resultado = calcular_total_pago(conta_id)

    print(resultado)


# ============================================================
# 7. ATUALIZANDO STATUS
# ============================================================

print("\n=== 6. ATUALIZANDO STATUS ===")

if ids_contas:

    conta_id = ids_contas[0]

    resultado = atualizar_status_conta(conta_id)

    print(resultado)


# ============================================================
# 8. TESTANDO FILTRO POR STATUS
# ============================================================

print("\n=== 7. CONTAS ABERTAS ===")

for conta in listar_contas(status="ABERTA"):
    print(conta)


# ============================================================
# 9. TESTANDO FILTRO POR DATA
# ============================================================

print("\n=== 8. CONTAS COM VENCIMENTO EM SETEMBRO ===")

for conta in listar_contas(
    data_inicio="2026-09-01",
    data_fim="2026-09-30"
):
    print(conta)


# ============================================================
# 10. TESTANDO DESPESA INEXISTENTE
# ============================================================

print("\n=== 9. TESTANDO DESPESA INEXISTENTE ===")

resultado = cadastrar_conta(
    despesa_id=99999,
    data_vencimento="2026-09-20",
    valor=10000,
)

print(resultado)


# ============================================================
# 11. TESTANDO VALOR INVÁLIDO
# ============================================================

print("\n=== 10. TESTANDO VALOR INVÁLIDO ===")

resultado = cadastrar_conta(
    despesa_id=despesa_internet,
    data_vencimento="2026-09-20",
    valor=0,
)

print(resultado)


# ============================================================
# 12. TESTANDO CANCELAMENTO
# ============================================================

print("\n=== 11. TESTANDO CANCELAMENTO ===")

if len(ids_contas) >= 4:

    conta_cancelar = ids_contas[3]

    resultado = cancelar_conta(conta_cancelar)

    print(resultado)


# ============================================================
# 13. CONFIRMANDO CANCELAMENTO
# ============================================================

print("\n=== 12. CONSULTANDO CONTA CANCELADA ===")

if len(ids_contas) >= 4:

    resultado = buscar_conta(ids_contas[3])

    print(resultado)


print("\n=== TESTE FINALIZADO ===")
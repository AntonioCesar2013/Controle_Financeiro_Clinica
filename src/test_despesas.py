from src.despesas import (
    cadastrar_setor,
    buscar_setor,
    listar_setores,
    desativar_setor,
    cadastrar_tipo_despesa,
    buscar_tipo_despesa,
    listar_tipos_despesa,
    desativar_tipo_despesa,
    cadastrar_despesa,
    buscar_despesa,
    listar_despesas,
    desativar_despesa,
)


print("=== TESTE DO MÓDULO DE DESPESAS ===")


# ============================================================
# 1. CADASTRANDO SETORES
# ============================================================

print("\n=== 1. CADASTRANDO SETORES ===")

setores = [
    "Administração",
    "Cozinha",
    "Transporte",
    "Manutenção",
    "Alojamento",
]

ids_setores = {}

for nome in setores:
    resultado = cadastrar_setor(nome)

    print(resultado)

    if resultado["sucesso"]:
        ids_setores[nome] = resultado["id"]


# ============================================================
# 2. LISTANDO SETORES
# ============================================================

print("\n=== 2. LISTANDO SETORES ===")

for setor in listar_setores():
    print(setor)


# ============================================================
# 3. CADASTRANDO TIPOS DE DESPESA
# ============================================================

print("\n=== 3. CADASTRANDO TIPOS DE DESPESA ===")

tipos = [
    "Internet",
    "Alimentação",
    "Combustível",
    "Manutenção",
    "Energia elétrica",
    "Água",
    "Material de limpeza",
]

ids_tipos = {}

for nome in tipos:
    resultado = cadastrar_tipo_despesa(nome)

    print(resultado)

    if resultado["sucesso"]:
        ids_tipos[nome] = resultado["id"]


# ============================================================
# 4. LISTANDO TIPOS
# ============================================================

print("\n=== 4. LISTANDO TIPOS DE DESPESA ===")

for tipo in listar_tipos_despesa():
    print(tipo)


# ============================================================
# 5. CADASTRANDO DESPESAS
# ============================================================

print("\n=== 5. CADASTRANDO DESPESAS ===")

despesas = [
    {
        "setor": "Administração",
        "tipo": "Internet",
        "descricao": "Internet da clínica",
        "natureza": "FIXA",
        "recorrente": True,
    },
    {
        "setor": "Cozinha",
        "tipo": "Alimentação",
        "descricao": "Compra de alimentos",
        "natureza": "VARIAVEL",
        "recorrente": True,
    },
    {
        "setor": "Transporte",
        "tipo": "Combustível",
        "descricao": "Combustível dos veículos",
        "natureza": "VARIAVEL",
        "recorrente": True,
    },
    {
        "setor": "Manutenção",
        "tipo": "Manutenção",
        "descricao": "Reparos gerais da clínica",
        "natureza": "EXTRAORDINARIA",
        "recorrente": False,
    },
    {
        "setor": "Administração",
        "tipo": "Energia elétrica",
        "descricao": "Conta de energia elétrica",
        "natureza": "FIXA",
        "recorrente": True,
    },
    {
        "setor": "Administração",
        "tipo": "Água",
        "descricao": "Conta de água",
        "natureza": "FIXA",
        "recorrente": True,
    },
    {
        "setor": "Administração",
        "tipo": "Material de limpeza",
        "descricao": "Produtos de limpeza",
        "natureza": "VARIAVEL",
        "recorrente": False,
    },
]

ids_despesas = []

for despesa in despesas:

    resultado = cadastrar_despesa(
        setor_id=ids_setores[despesa["setor"]],
        tipo_despesa_id=ids_tipos[despesa["tipo"]],
        descricao=despesa["descricao"],
        natureza=despesa["natureza"],
        recorrente=despesa["recorrente"],
    )

    print(resultado)

    if resultado["sucesso"]:
        ids_despesas.append(resultado["id"])


# ============================================================
# 6. LISTANDO DESPESAS
# ============================================================

print("\n=== 6. LISTANDO DESPESAS ===")

for despesa in listar_despesas():
    print(despesa)


# ============================================================
# 7. BUSCANDO UMA DESPESA
# ============================================================

print("\n=== 7. BUSCANDO UMA DESPESA ===")

if ids_despesas:
    resultado = buscar_despesa(ids_despesas[0])
    print(resultado)


# ============================================================
# 8. TESTANDO NATUREZA INVÁLIDA
# ============================================================

print("\n=== 8. TESTANDO NATUREZA INVÁLIDA ===")

resultado = cadastrar_despesa(
    setor_id=ids_setores["Administração"],
    tipo_despesa_id=ids_tipos["Internet"],
    descricao="Despesa inválida para teste",
    natureza="ERRADA",
    recorrente=False,
)

print(resultado)


# ============================================================
# 9. TESTANDO SETOR INEXISTENTE
# ============================================================

print("\n=== 9. TESTANDO SETOR INEXISTENTE ===")

resultado = cadastrar_despesa(
    setor_id=99999,
    tipo_despesa_id=ids_tipos["Internet"],
    descricao="Teste de setor inexistente",
    natureza="FIXA",
    recorrente=True,
)

print(resultado)


# ============================================================
# 10. TESTANDO TIPO INEXISTENTE
# ============================================================

print("\n=== 10. TESTANDO TIPO INEXISTENTE ===")

resultado = cadastrar_despesa(
    setor_id=ids_setores["Administração"],
    tipo_despesa_id=99999,
    descricao="Teste de tipo inexistente",
    natureza="FIXA",
    recorrente=True,
)

print(resultado)


# ============================================================
# 11. DESATIVANDO UMA DESPESA
# ============================================================

print("\n=== 11. DESATIVANDO UMA DESPESA ===")

if ids_despesas:
    resultado = desativar_despesa(ids_despesas[-1])
    print(resultado)


# ============================================================
# 12. LISTANDO NOVAMENTE
# ============================================================

print("\n=== 12. DESPESAS ATIVAS ===")

for despesa in listar_despesas():
    print(despesa)


print("\n=== TESTE FINALIZADO ===")
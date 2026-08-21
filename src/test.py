from src.residentes import cadastrar_residente
from src.responsaveis import cadastrar_responsavel
from src.residente_responsavel import (
    vincular_responsavel,
    buscar_responsaveis_do_residente,
    remover_vinculo
)


print("=== 1. CADASTRANDO RESIDENTE ===")

residente = cadastrar_residente(
    "João da Silva",
    "12345678900",
    "Curitiba"
)

print(residente)


print("\n=== 2. CADASTRANDO RESPONSÁVEL ===")

responsavel = cadastrar_responsavel(
    "Maria da Silva",
    "98765432100",
    "(41) 99999-9999",
    "maria@email.com"
)

print(responsavel)


print("\n=== 3. CRIANDO VÍNCULO ===")

vinculo = vincular_responsavel(
    residente["id"],
    responsavel["id"],
    "Mãe",
    1
)

print(vinculo)


print("\n=== 4. BUSCANDO RESPONSÁVEIS ===")

lista = buscar_responsaveis_do_residente(
    residente["id"]
)

for item in lista:
    print(item)


print("\n=== 5. TENTANDO CRIAR O MESMO VÍNCULO NOVAMENTE ===")

duplicado = vincular_responsavel(
    residente["id"],
    responsavel["id"],
    "Mãe",
    1
)

print(duplicado)


print("\n=== 6. REMOVENDO VÍNCULO ===")

removido = remover_vinculo(
    vinculo["id"]
)

print("Removido:", removido)


print("\n=== 7. BUSCANDO NOVAMENTE ===")

lista = buscar_responsaveis_do_residente(
    residente["id"]
)

print(lista)
from src.residentes import cadastrar_residente
from src.responsaveis import cadastrar_responsavel
from src.internacoes import (
    cadastrar_internacao,
    buscar_internacao
)
from src.cobrancas import (
    gerar_cobrancas,
    buscar_cobrancas
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


print("\n=== 3. CADASTRANDO INTERNAÇÃO ===")

resultado = cadastrar_internacao(
    residente_id=residente["id"],
    responsavel_id=responsavel["id"],
    data_acolhimento="2026-08-10",
    periodo_tratamento=3,
    valor_contrato=8500,
    valor_acolhimento=1000,
    valor_mensalidade=2500
)

print(resultado)


if resultado["sucesso"]:

    print("\n=== 4. BUSCANDO INTERNAÇÃO ===")

    internacao = buscar_internacao(
        resultado["id"]
    )

    print(internacao)


    print("\n=== 5. GERANDO COBRANÇAS ===")

    resultado_cobrancas = gerar_cobrancas(
        resultado["id"]
    )

    print(resultado_cobrancas)


    if resultado_cobrancas["sucesso"]:

        print("\n=== 6. COBRANÇAS GERADAS ===")

        cobrancas = buscar_cobrancas(
            resultado["id"]
        )

        for cobranca in cobrancas:
            print(cobranca)
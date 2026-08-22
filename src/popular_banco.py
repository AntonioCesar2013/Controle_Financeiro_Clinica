
import sqlite3

from src.banco import CAMINHO_BANCO
from src.residentes import cadastrar_residente
from src.responsaveis import cadastrar_responsavel
from src.internacoes import cadastrar_internacao
from src.cobrancas import gerar_cobrancas
from src.pagamentos import registrar_pagamento


def limpar_banco():
    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()

    # Apaga primeiro as tabelas que possuem relacionamentos
    cursor.execute("DELETE FROM pagamentos")
    cursor.execute("DELETE FROM cobrancas")
    cursor.execute("DELETE FROM internacoes")
    cursor.execute("DELETE FROM residente_responsavel")
    cursor.execute("DELETE FROM responsaveis")
    cursor.execute("DELETE FROM residentes")

    conexao.commit()
    conexao.close()


def buscar_cobranca(internacao_id, tipo=None, numero_parcela=None):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()

    if tipo is not None:
        cursor.execute(
            """
            SELECT id
            FROM cobrancas
            WHERE internacao_id = ?
            AND tipo = ?
            """,
            (internacao_id, tipo)
        )

    else:
        cursor.execute(
            """
            SELECT id
            FROM cobrancas
            WHERE internacao_id = ?
            AND numero_parcela = ?
            """,
            (internacao_id, numero_parcela)
        )

    resultado = cursor.fetchone()

    conexao.close()

    if resultado:
        return resultado[0]

    return None


def popular_banco():

    print("=== LIMPANDO BANCO ===")
    limpar_banco()


    # =========================================================
    # RESIDENTES
    # =========================================================

    print("\n=== CADASTRANDO RESIDENTES ===")

    residente1 = cadastrar_residente(
        "João da Silva",
        "11111111111",
        "Curitiba"
    )

    residente2 = cadastrar_residente(
        "Carlos Oliveira",
        "22222222222",
        "Cascavel"
    )

    residente3 = cadastrar_residente(
        "Pedro Santos",
        "33333333333",
        "Foz do Iguaçu"
    )

    residente4 = cadastrar_residente(
        "Lucas Ferreira",
        "44444444444",
        "Londrina"
    )

    residente5 = cadastrar_residente(
        "Marcos Souza",
        "55555555555",
        "Maringá"
    )

    print(residente1)
    print(residente2)
    print(residente3)
    print(residente4)
    print(residente5)


    # =========================================================
    # RESPONSÁVEIS
    # =========================================================

    print("\n=== CADASTRANDO RESPONSÁVEIS ===")

    responsavel1 = cadastrar_responsavel(
        "Maria da Silva",
        "66666666666",
        "(41) 99999-1111",
        "maria@email.com"
    )

    responsavel2 = cadastrar_responsavel(
        "Ana Oliveira",
        "77777777777",
        "(45) 99999-2222",
        "ana@email.com"
    )

    responsavel3 = cadastrar_responsavel(
        "José Santos",
        "88888888888",
        "(45) 99999-3333",
        "jose@email.com"
    )

    responsavel4 = cadastrar_responsavel(
        "Fernanda Ferreira",
        "99999999999",
        "(43) 99999-4444",
        "fernanda@email.com"
    )

    responsavel5 = cadastrar_responsavel(
        "Paulo Souza",
        "10101010101",
        "(44) 99999-5555",
        "paulo@email.com"
    )

    print(responsavel1)
    print(responsavel2)
    print(responsavel3)
    print(responsavel4)
    print(responsavel5)


    # =========================================================
    # INTERNAÇÕES
    # =========================================================

    print("\n=== CADASTRANDO INTERNAÇÕES ===")

    # R$ 1.000 + (R$ 2.500 x 3) = R$ 8.500
    internacao1 = cadastrar_internacao(
        residente_id=residente1["id"],
        responsavel_id=responsavel1["id"],
        data_acolhimento="2026-08-10",
        periodo_tratamento=3,
        valor_contrato=8500,
        valor_acolhimento=1000,
        valor_mensalidade=2500
    )

    # R$ 1.000 + (R$ 2.000 x 4) = R$ 9.000
    internacao2 = cadastrar_internacao(
        residente_id=residente2["id"],
        responsavel_id=responsavel2["id"],
        data_acolhimento="2026-07-15",
        periodo_tratamento=4,
        valor_contrato=9000,
        valor_acolhimento=1000,
        valor_mensalidade=2000
    )

    # R$ 1.000 + (R$ 2.500 x 6) = R$ 16.000
    internacao3 = cadastrar_internacao(
        residente_id=residente3["id"],
        responsavel_id=responsavel3["id"],
        data_acolhimento="2026-08-01",
        periodo_tratamento=6,
        valor_contrato=16000,
        valor_acolhimento=1000,
        valor_mensalidade=2500
    )

    # R$ 1.000 + (R$ 3.000 x 3) = R$ 10.000
    internacao4 = cadastrar_internacao(
        residente_id=residente4["id"],
        responsavel_id=responsavel4["id"],
        data_acolhimento="2026-06-20",
        periodo_tratamento=3,
        valor_contrato=10000,
        valor_acolhimento=1000,
        valor_mensalidade=3000
    )

    # R$ 2.000 + (R$ 3.000 x 5) = R$ 17.000
    internacao5 = cadastrar_internacao(
        residente_id=residente5["id"],
        responsavel_id=responsavel5["id"],
        data_acolhimento="2026-05-05",
        periodo_tratamento=5,
        valor_contrato=17000,
        valor_acolhimento=2000,
        valor_mensalidade=3000
    )

    print(internacao1)
    print(internacao2)
    print(internacao3)
    print(internacao4)
    print(internacao5)


    # =========================================================
    # COBRANÇAS
    # =========================================================

    print("\n=== GERANDO COBRANÇAS ===")

    internacoes = [
        internacao1,
        internacao2,
        internacao3,
        internacao4,
        internacao5
    ]

    for internacao in internacoes:
        gerar_cobrancas(internacao["id"])

    print("Cobranças geradas para todas as internações.")


    # =========================================================
    # PAGAMENTOS
    # =========================================================

    print("\n=== REGISTRANDO PAGAMENTOS ===")


    # ---------------------------------------------------------
    # JOÃO
    #
    # Acolhimento pago
    # Primeira mensalidade parcialmente paga
    # ---------------------------------------------------------

    cobranca_id = buscar_cobranca(
        internacao1["id"],
        tipo="ACOLHIMENTO"
    )

    registrar_pagamento(
        cobranca_id=cobranca_id,
        data_pagamento="2026-08-10",
        valor=1000,
        forma_pagamento="PIX",
        observacao="Acolhimento pago"
    )

    cobranca_id = buscar_cobranca(
        internacao1["id"],
        numero_parcela=1
    )

    registrar_pagamento(
        cobranca_id=cobranca_id,
        data_pagamento="2026-09-10",
        valor=1000,
        forma_pagamento="PIX",
        observacao="Pagamento parcial da mensalidade"
    )


    # ---------------------------------------------------------
    # CARLOS
    #
    # Acolhimento pago
    # Primeira mensalidade paga integralmente
    # Segunda mensalidade paga integralmente
    # ---------------------------------------------------------

    cobranca_id = buscar_cobranca(
        internacao2["id"],
        tipo="ACOLHIMENTO"
    )

    registrar_pagamento(
        cobranca_id=cobranca_id,
        data_pagamento="2026-07-15",
        valor=1000,
        forma_pagamento="DINHEIRO",
        observacao="Acolhimento"
    )

    cobranca_id = buscar_cobranca(
        internacao2["id"],
        numero_parcela=1
    )

    registrar_pagamento(
        cobranca_id=cobranca_id,
        data_pagamento="2026-08-15",
        valor=2000,
        forma_pagamento="PIX",
        observacao="Mensalidade paga"
    )

    cobranca_id = buscar_cobranca(
        internacao2["id"],
        numero_parcela=2
    )

    registrar_pagamento(
        cobranca_id=cobranca_id,
        data_pagamento="2026-09-15",
        valor=2000,
        forma_pagamento="TRANSFERENCIA",
        observacao="Mensalidade paga"
    )


    # ---------------------------------------------------------
    # PEDRO
    #
    # Acolhimento pago
    # Primeira mensalidade dividida em dois pagamentos
    # ---------------------------------------------------------

    cobranca_id = buscar_cobranca(
        internacao3["id"],
        tipo="ACOLHIMENTO"
    )

    registrar_pagamento(
        cobranca_id=cobranca_id,
        data_pagamento="2026-08-01",
        valor=1000,
        forma_pagamento="DEPOSITO",
        observacao="Acolhimento"
    )

    cobranca_id = buscar_cobranca(
        internacao3["id"],
        numero_parcela=1
    )

    registrar_pagamento(
        cobranca_id=cobranca_id,
        data_pagamento="2026-09-01",
        valor=1500,
        forma_pagamento="PIX",
        observacao="Primeira parte da mensalidade"
    )

    registrar_pagamento(
        cobranca_id=cobranca_id,
        data_pagamento="2026-09-05",
        valor=1000,
        forma_pagamento="DINHEIRO",
        observacao="Segunda parte da mensalidade"
    )


    # ---------------------------------------------------------
    # LUCAS
    #
    # Acolhimento pago
    # Nenhuma mensalidade paga ainda
    # ---------------------------------------------------------

    cobranca_id = buscar_cobranca(
        internacao4["id"],
        tipo="ACOLHIMENTO"
    )

    registrar_pagamento(
        cobranca_id=cobranca_id,
        data_pagamento="2026-06-20",
        valor=1000,
        forma_pagamento="PIX",
        observacao="Acolhimento"
    )


    # ---------------------------------------------------------
    # MARCOS
    #
    # Acolhimento parcialmente pago
    # Nenhuma mensalidade paga
    # ---------------------------------------------------------

    cobranca_id = buscar_cobranca(
        internacao5["id"],
        tipo="ACOLHIMENTO"
    )

    registrar_pagamento(
        cobranca_id=cobranca_id,
        data_pagamento="2026-05-05",
        valor=1000,
        forma_pagamento="DINHEIRO",
        observacao="Pagamento parcial do acolhimento"
    )


    print("Pagamentos fictícios registrados.")


    # =========================================================
    # FINAL
    # =========================================================

    print("\n=== BANCO POPULADO COM SUCESSO ===")

    print("\nCenários criados:")

    print("- João: mensalidade parcialmente paga")
    print("- Carlos: mensalidades pagas")
    print("- Pedro: mensalidade paga em duas partes")
    print("- Lucas: somente acolhimento pago")
    print("- Marcos: acolhimento parcialmente pago")


if __name__ == "__main__":
    popular_banco()

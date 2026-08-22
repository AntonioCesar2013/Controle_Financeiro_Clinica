import sqlite3

from src.banco import CAMINHO_BANCO


def registrar_pagamento(
    cobranca_id,
    data_pagamento,
    valor,
    forma_pagamento,
    observacao=None
):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    # Busca a cobrança
    cursor.execute(
        """
        SELECT
            id,
            valor,
            status
        FROM cobrancas
        WHERE id = ?
        """,
        (cobranca_id,)
    )

    cobranca = cursor.fetchone()

    if cobranca is None:
        conexao.close()

        return {
            "sucesso": False,
            "erro": "Cobrança não encontrada."
        }

    # Valor da cobrança
    valor_cobranca = cobranca["valor"]

    # Soma tudo que já foi pago
    cursor.execute(
        """
        SELECT COALESCE(SUM(valor), 0)
        FROM pagamentos
        WHERE cobranca_id = ?
        """,
        (cobranca_id,)
    )

    total_pago = cursor.fetchone()[0]

    # Calcula quanto ainda falta
    restante = valor_cobranca - total_pago

    if valor <= 0:
        conexao.close()

        return {
            "sucesso": False,
            "erro": "O valor do pagamento deve ser maior que zero."
        }

    if valor > restante:
        conexao.close()

        return {
            "sucesso": False,
            "erro": (
                f"Pagamento excede o valor restante da cobrança. "
                f"Restante: R$ {restante}"
            )
        }

    # Registra o pagamento
    cursor.execute(
        """
        INSERT INTO pagamentos (
            cobranca_id,
            data_pagamento,
            valor,
            forma_pagamento,
            observacao
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            cobranca_id,
            data_pagamento,
            valor,
            forma_pagamento,
            observacao
        )
    )

    pagamento_id = cursor.lastrowid

    # Novo total pago
    novo_total_pago = total_pago + valor

    # Atualiza o status da cobrança
    if novo_total_pago == valor_cobranca:
        novo_status = "PAGA"
    else:
        novo_status = "PARCIAL"

    cursor.execute(
        """
        UPDATE cobrancas
        SET status = ?
        WHERE id = ?
        """,
        (
            novo_status,
            cobranca_id
        )
    )

    conexao.commit()
    conexao.close()

    return {
        "sucesso": True,
        "id": pagamento_id,
        "cobranca_id": cobranca_id,
        "valor": valor,
        "total_pago": novo_total_pago,
        "restante": valor_cobranca - novo_total_pago,
        "status": novo_status
    }


def buscar_pagamentos(cobranca_id):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            id,
            cobranca_id,
            data_pagamento,
            valor,
            forma_pagamento,
            observacao
        FROM pagamentos
        WHERE cobranca_id = ?
        ORDER BY data_pagamento, id
        """,
        (cobranca_id,)
    )

    pagamentos = cursor.fetchall()

    conexao.close()

    return [dict(pagamento) for pagamento in pagamentos]


def resumo_cobranca(cobranca_id):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            id,
            valor,
            status
        FROM cobrancas
        WHERE id = ?
        """,
        (cobranca_id,)
    )

    cobranca = cursor.fetchone()

    if cobranca is None:
        conexao.close()

        return {
            "sucesso": False,
            "erro": "Cobrança não encontrada."
        }

    cursor.execute(
        """
        SELECT COALESCE(SUM(valor), 0)
        FROM pagamentos
        WHERE cobranca_id = ?
        """,
        (cobranca_id,)
    )

    total_pago = cursor.fetchone()[0]

    restante = cobranca["valor"] - total_pago

    conexao.close()

    return {
        "sucesso": True,
        "cobranca_id": cobranca["id"],
        "valor_cobranca": cobranca["valor"],
        "total_pago": total_pago,
        "restante": restante,
        "status": cobranca["status"]
    }
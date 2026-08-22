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
            desconto,
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

    if cobranca["status"] == "DESCONTADA":
        conexao.close()

        return {
            "sucesso": False,
            "erro": (
                "Não é possível registrar recebimento de uma cobrança "
                "totalmente descontada."
            )
        }

    # Valor líquido da cobrança
    valor_cobranca = cobranca["valor"]
    desconto = cobranca["desconto"]
    valor_devido = valor_cobranca - desconto

    if valor_devido == 0:
        conexao.close()

        return {
            "sucesso": False,
            "erro": "Não é possível registrar recebimento de uma cobrança sem valor devido."
        }

    # Soma tudo que já foi pago
    cursor.execute(
        """
        SELECT COALESCE(SUM(valor), 0)
        FROM recebimentos
        WHERE cobranca_id = ?
        """,
        (cobranca_id,)
    )

    total_pago = cursor.fetchone()[0]

    # Calcula quanto ainda falta
    restante = valor_devido - total_pago

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
        INSERT INTO recebimentos (
            cobranca_id,
            data_recebimento,
            valor,
            forma_recebimento,
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
    if novo_total_pago == valor_devido:
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
        "restante": valor_devido - novo_total_pago,
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
            data_recebimento,
            valor,
            forma_recebimento,
            observacao
        FROM recebimentos
        WHERE cobranca_id = ?
        ORDER BY data_recebimento, id
        """,
        (cobranca_id,)
    )

    pagamentos = cursor.fetchall()

    conexao.close()

    return [dict(pagamento) for pagamento in pagamentos]


def buscar_recebimento(recebimento_id):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            SELECT
                id,
                cobranca_id,
                data_recebimento,
                valor,
                forma_recebimento,
                observacao
            FROM recebimentos
            WHERE id = ?
            """,
            (recebimento_id,)
        )

        recebimento = cursor.fetchone()

        if recebimento is None:
            return {
                "sucesso": False,
                "erro": "Recebimento não encontrado."
            }

        return {
            "sucesso": True,
            **dict(recebimento)
        }
    finally:
        conexao.close()


def excluir_recebimento(recebimento_id):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            SELECT
                id,
                cobranca_id
            FROM recebimentos
            WHERE id = ?
            """,
            (recebimento_id,)
        )

        recebimento = cursor.fetchone()

        if recebimento is None:
            return {
                "sucesso": False,
                "erro": "Recebimento não encontrado."
            }

        cobranca_id = recebimento["cobranca_id"]

        cursor.execute(
            """
            SELECT
                id,
                valor,
                desconto,
                status
            FROM cobrancas
            WHERE id = ?
            """,
            (cobranca_id,)
        )

        cobranca = cursor.fetchone()

        if cobranca is None:
            return {
                "sucesso": False,
                "erro": "Cobrança relacionada não encontrada."
            }

        cursor.execute(
            """
            DELETE FROM recebimentos
            WHERE id = ?
            """,
            (recebimento_id,)
        )

        cursor.execute(
            """
            SELECT COALESCE(SUM(valor), 0)
            FROM recebimentos
            WHERE cobranca_id = ?
            """,
            (cobranca_id,)
        )

        total_recebido = cursor.fetchone()[0]
        valor_devido = cobranca["valor"] - cobranca["desconto"]

        if valor_devido == 0:
            novo_status = "DESCONTADA"
        elif total_recebido == 0:
            novo_status = "ABERTA"
        elif total_recebido < valor_devido:
            novo_status = "PARCIAL"
        elif total_recebido == valor_devido:
            novo_status = "PAGA"
        else:
            raise ValueError(
                "Os recebimentos registrados ultrapassam o valor devido da cobrança."
            )

        cursor.execute(
            """
            UPDATE cobrancas
            SET status = ?
            WHERE id = ?
            """,
            (novo_status, cobranca_id)
        )

        conexao.commit()

        return {
            "sucesso": True,
            "id": recebimento_id,
            "cobranca_id": cobranca_id,
            "total_recebido": total_recebido,
            "restante": valor_devido - total_recebido,
            "status": novo_status
        }
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def resumo_cobranca(cobranca_id):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            id,
            valor,
            desconto,
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
        FROM recebimentos
        WHERE cobranca_id = ?
        """,
        (cobranca_id,)
    )

    total_pago = cursor.fetchone()[0]

    valor_devido = cobranca["valor"] - cobranca["desconto"]
    restante = valor_devido - total_pago

    conexao.close()

    return {
        "sucesso": True,
        "cobranca_id": cobranca["id"],
        "valor_cobranca": cobranca["valor"],
        "desconto": cobranca["desconto"],
        "valor_devido": valor_devido,
        "total_pago": total_pago,
        "restante": restante,
        "status": cobranca["status"]
    }

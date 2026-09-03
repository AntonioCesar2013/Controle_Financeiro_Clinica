from datetime import datetime
import sqlite3

from src.infraestrutura.banco import conectar


# ============================================================
# UTILITÁRIOS
# ============================================================

def _nova_conexao():
    """
    Cria uma conexão com o banco já configurada para retornar
    registros SQLite como sqlite3.Row.

    Isso permite utilizar:

        dict(row)

    nas consultas que retornam registros.
    """

    conn = conectar()
    conn.row_factory = sqlite3.Row

    return conn


def _validar_valor(valor):
    """
    Valida um valor já convertido para centavos.

    Exemplos:
        125000 = R$ 1.250,00
        50000  = R$ 500,00
        1      = R$ 0,01
    """

    try:
        valor = int(valor)
    except (TypeError, ValueError):
        raise ValueError("O valor do pagamento deve ser numérico.")

    if valor <= 0:
        raise ValueError("O valor do pagamento deve ser maior que zero.")

    return valor


def _validar_data(data):
    """
    Valida uma data no formato YYYY-MM-DD.

    Exemplos válidos:
        2026-09-10
        2026-12-31

    Exemplos inválidos:
        10/09/2026
        09-10-2026
        2026/09/10
    """

    if not isinstance(data, str):
        return False

    try:
        data_convertida = datetime.strptime(
            data,
            "%Y-%m-%d"
        )

        # Garante que o formato informado seja exatamente
        # YYYY-MM-DD.
        return data_convertida.strftime("%Y-%m-%d") == data

    except ValueError:
        return False


# ============================================================
# BUSCAR CONTA
# ============================================================

def _buscar_conta(conn, conta_pagar_id):
    """
    Busca uma conta a pagar.
    """

    cursor = conn.execute(
        """
        SELECT
            cp.id,
            cp.despesa_id,
            cp.data_vencimento,
            cp.valor,
            cp.status
        FROM contas_pagar cp
        WHERE cp.id = ?
        """,
        (conta_pagar_id,)
    )

    return cursor.fetchone()


# ============================================================
# TOTAL PAGO
# ============================================================

def _total_pago(conn, conta_pagar_id):
    """
    Retorna o total já pago da conta.
    """

    cursor = conn.execute(
        """
        SELECT COALESCE(SUM(valor), 0)
        FROM pagamentos_saida
        WHERE conta_pagar_id = ?
        """,
        (conta_pagar_id,)
    )

    return cursor.fetchone()[0]


# ============================================================
# ATUALIZAR STATUS
# ============================================================

def _atualizar_status(conn, conta_pagar_id):
    """
    Atualiza automaticamente o status da conta.

    Regras:

        0 pago
            -> ABERTA

        parcial
            -> PARCIAL

        valor total pago
            -> PAGA

        CANCELADA
            -> permanece CANCELADA
    """

    conta = _buscar_conta(
        conn,
        conta_pagar_id
    )

    if not conta:
        return {
            "sucesso": False,
            "erro": "Conta a pagar não encontrada."
        }

    valor_conta = conta["valor"]
    status_atual = conta["status"]

    total_pago = _total_pago(
        conn,
        conta_pagar_id
    )

    restante = max(
        valor_conta - total_pago,
        0
    )

    # Conta cancelada não sofre alteração.
    if status_atual == "CANCELADA":
        return {
            "sucesso": True,
            "status": "CANCELADA",
            "total_pago": total_pago,
            "restante": restante
        }

    if total_pago == 0:
        novo_status = "ABERTA"

    elif total_pago < valor_conta:
        novo_status = "PARCIAL"

    else:
        novo_status = "PAGA"

    conn.execute(
        """
        UPDATE contas_pagar
        SET status = ?
        WHERE id = ?
        """,
        (
            novo_status,
            conta_pagar_id
        )
    )

    return {
        "sucesso": True,
        "status": novo_status,
        "total_pago": total_pago,
        "restante": restante
    }


# ============================================================
# REGISTRAR PAGAMENTO
# ============================================================

def registrar_pagamento(
    conta_pagar_id,
    data_pagamento,
    valor,
    forma_pagamento=None,
    observacao=None
):
    """
    Registra um pagamento de saída.

    IMPORTANTE:
    O valor deve ser informado em CENTAVOS.

    Exemplo:

        registrar_pagamento(
            conta_pagar_id=1,
            data_pagamento="2026-09-10",
            valor=50000,
            forma_pagamento="PIX"
        )

    significa um pagamento de R$ 500,00.
    """

    # --------------------------------------------------------
    # VALIDAR VALOR
    # --------------------------------------------------------

    try:
        valor = _validar_valor(valor)

    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": str(erro)
        }

    # --------------------------------------------------------
    # VALIDAR DATA
    # --------------------------------------------------------

    if not _validar_data(data_pagamento):
        return {
            "sucesso": False,
            "erro": "Data de pagamento inválida. Use YYYY-MM-DD."
        }

    # --------------------------------------------------------
    # FORMA DE PAGAMENTO PADRÃO
    # --------------------------------------------------------

    forma_pagamento = str(forma_pagamento or "PIX").strip().upper() or "PIX"

    conn = _nova_conexao()

    try:
        conn.execute("BEGIN IMMEDIATE")

        # ----------------------------------------------------
        # BUSCAR CONTA
        # ----------------------------------------------------

        conta = _buscar_conta(
            conn,
            conta_pagar_id
        )

        if not conta:
            return {
                "sucesso": False,
                "erro": "Conta a pagar não encontrada."
            }

        valor_conta = conta["valor"]
        status_conta = conta["status"]

        # ----------------------------------------------------
        # CONTA CANCELADA
        # ----------------------------------------------------

        if status_conta == "CANCELADA":
            return {
                "sucesso": False,
                "erro": "Não é possível pagar uma conta cancelada."
            }

        # ----------------------------------------------------
        # VALOR JÁ PAGO
        # ----------------------------------------------------

        total_pago = _total_pago(
            conn,
            conta_pagar_id
        )

        restante = valor_conta - total_pago

        # ----------------------------------------------------
        # CONTA JÁ PAGA
        # ----------------------------------------------------

        if restante <= 0:
            return {
                "sucesso": False,
                "erro": "A conta já está totalmente paga."
            }

        # ----------------------------------------------------
        # PAGAMENTO ACIMA DO RESTANTE
        # ----------------------------------------------------

        if valor > restante:
            return {
                "sucesso": False,
                "erro": (
                    "Pagamento excede o valor restante da conta. "
                    f"Restante: R$ {restante / 100:.2f}"
                )
            }

        # ----------------------------------------------------
        # NORMALIZAR FORMA DE PAGAMENTO
        # ----------------------------------------------------

        # ----------------------------------------------------
        # REGISTRAR PAGAMENTO
        # ----------------------------------------------------

        cursor = conn.execute(
            """
            INSERT INTO pagamentos_saida (
                conta_pagar_id,
                data_pagamento,
                valor,
                forma_pagamento,
                observacao
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                conta_pagar_id,
                data_pagamento,
                valor,
                forma_pagamento,
                observacao
            )
        )

        pagamento_id = cursor.lastrowid

        # ----------------------------------------------------
        # ATUALIZAR STATUS
        # ----------------------------------------------------

        status = _atualizar_status(
            conn,
            conta_pagar_id
        )

        conn.commit()

        return {
            "sucesso": True,
            "id": pagamento_id,
            "conta_pagar_id": conta_pagar_id,
            "data_pagamento": data_pagamento,
            "valor": valor,
            "forma_pagamento": forma_pagamento,
            "total_pago": status["total_pago"],
            "restante": status["restante"],
            "status": status["status"]
        }

    except sqlite3.Error as erro:

        conn.rollback()

        return {
            "sucesso": False,
            "erro": f"Erro no banco de dados: {erro}"
        }

    finally:
        conn.close()


# ============================================================
# RESUMO DA CONTA
# ============================================================

def resumo_conta(conta_pagar_id):
    """
    Retorna o resumo financeiro da conta.
    """

    conn = _nova_conexao()

    try:

        conta = _buscar_conta(
            conn,
            conta_pagar_id
        )

        if not conta:
            return {
                "sucesso": False,
                "erro": "Conta a pagar não encontrada."
            }

        valor_conta = conta["valor"]

        total_pago = _total_pago(
            conn,
            conta_pagar_id
        )

        restante = max(
            valor_conta - total_pago,
            0
        )

        return {
            "sucesso": True,
            "conta_pagar_id": conta_pagar_id,
            "valor_conta": valor_conta,
            "total_pago": total_pago,
            "restante": restante,
            "status": conta["status"]
        }

    finally:
        conn.close()


# ============================================================
# LISTAR PAGAMENTOS
# ============================================================

def listar_pagamentos(conta_pagar_id):
    """
    Lista todos os pagamentos realizados para uma conta.
    """

    conn = _nova_conexao()

    try:

        cursor = conn.execute(
            """
            SELECT
                p.id,
                p.conta_pagar_id,
                p.data_pagamento,
                p.valor,
                p.forma_pagamento,
                p.observacao,
                c.data_vencimento,
                d.descricao AS despesa_descricao,
                s.nome AS setor_nome,
                d.natureza

            FROM pagamentos_saida p

            INNER JOIN contas_pagar c
                ON c.id = p.conta_pagar_id

            INNER JOIN despesas d
                ON d.id = c.despesa_id

            INNER JOIN setores s
                ON s.id = d.setor_id

            WHERE p.conta_pagar_id = ?

            ORDER BY
                p.data_pagamento,
                p.id
            """,
            (conta_pagar_id,)
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        conn.close()


# ============================================================
# BUSCAR PAGAMENTO
# ============================================================

def buscar_pagamento(pagamento_id):
    """
    Busca um pagamento específico.
    """

    conn = _nova_conexao()

    try:

        cursor = conn.execute(
            """
            SELECT
                ps.id,
                ps.conta_pagar_id,
                ps.data_pagamento,
                ps.valor,
                ps.forma_pagamento,
                ps.observacao,
                cp.data_vencimento,
                d.descricao AS despesa_descricao,
                s.nome AS setor_nome,
                d.natureza

            FROM pagamentos_saida ps

            INNER JOIN contas_pagar cp
                ON cp.id = ps.conta_pagar_id

            INNER JOIN despesas d
                ON d.id = cp.despesa_id

            INNER JOIN setores s
                ON s.id = d.setor_id

            WHERE ps.id = ?
            """,
            (pagamento_id,)
        )

        pagamento = cursor.fetchone()

        if not pagamento:
            return {
                "sucesso": False,
                "erro": "Pagamento não encontrado."
            }

        return {
            "sucesso": True,
            **dict(pagamento)
        }

    finally:
        conn.close()


# ============================================================
# EXCLUIR PAGAMENTO
# ============================================================

def excluir_pagamento(pagamento_id, motivo=None):
    """
    Exclui um pagamento.

    Depois da exclusão, o status da conta é recalculado.
    """

    conn = _nova_conexao()

    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.execute(
            """
            SELECT
                id,
                conta_pagar_id
            FROM pagamentos_saida
            WHERE id = ?
            """,
            (pagamento_id,)
        )

        pagamento = cursor.fetchone()

        if not pagamento:
            return {
                "sucesso": False,
                "erro": "Pagamento não encontrado."
            }

        conta_pagar_id = pagamento["conta_pagar_id"]

        conta = _buscar_conta(
            conn,
            conta_pagar_id
        )

        if not conta:
            return {
                "sucesso": False,
                "erro": "Conta a pagar relacionada não encontrada."
            }

        if conta["status"] == "CANCELADA":
            return {
                "sucesso": False,
                "erro": (
                    "Não é possível alterar pagamentos "
                    "de uma conta cancelada."
                )
            }

        from src.financeiro.estornos import preservar
        preservar(conn, "pagamentos_saida", pagamento_id, motivo)
        conn.execute(
            """
            DELETE FROM pagamentos_saida
            WHERE id = ?
            """,
            (pagamento_id,)
        )

        status = _atualizar_status(
            conn,
            conta_pagar_id
        )

        conn.commit()

        return {
            "sucesso": True,
            "id": pagamento_id,
            "conta_pagar_id": conta_pagar_id,
            "total_pago": status["total_pago"],
            "restante": status["restante"],
            "status": status["status"]
        }

    except sqlite3.Error as erro:

        conn.rollback()

        return {
            "sucesso": False,
            "erro": f"Erro no banco de dados: {erro}"
        }

    finally:
        conn.close()


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    print("Módulo de pagamentos carregado com sucesso.")

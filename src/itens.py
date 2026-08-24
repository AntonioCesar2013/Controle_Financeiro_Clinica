import sqlite3

from src.banco import CAMINHO_BANCO


def cadastrar_item(nome):
    """Cadastra um novo item no catálogo."""

    nome = nome.strip()

    if not nome:
        return {
            "sucesso": False,
            "erro": "O nome do item é obrigatório."
        }

    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO item (
                nome
            )
            VALUES (?)
            """,
            (nome,)
        )

        item_id = cursor.lastrowid

        conexao.commit()

        return {
            "sucesso": True,
            "id": item_id,
            "nome": nome
        }

    except sqlite3.IntegrityError:
        conexao.rollback()

        return {
            "sucesso": False,
            "erro": "Já existe um item com esse nome."
        }

    finally:
        conexao.close()


def buscar_item(item_id):
    """Busca um item pelo ID."""

    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                id,
                nome,
                ativo
            FROM item
            WHERE id = ?
            """,
            (item_id,)
        )

        item = cursor.fetchone()

        if item is None:
            return {
                "sucesso": False,
                "erro": "Item não encontrado."
            }

        return {
            "sucesso": True,
            **dict(item)
        }

    finally:
        conexao.close()


def listar_itens(apenas_ativos=True):
    """Lista os itens cadastrados."""

    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    try:
        cursor = conexao.cursor()

        if apenas_ativos:
            cursor.execute(
                """
                SELECT
                    id,
                    nome,
                    ativo
                FROM item
                WHERE ativo = 1
                ORDER BY nome
                """
            )
        else:
            cursor.execute(
                """
                SELECT
                    id,
                    nome,
                    ativo
                FROM item
                ORDER BY nome
                """
            )

        itens = cursor.fetchall()

        return [dict(item) for item in itens]

    finally:
        conexao.close()


def alterar_status_item(item_id, ativo):
    """Ativa ou desativa um item."""

    if ativo not in (0, 1):
        return {
            "sucesso": False,
            "erro": "O status deve ser 0 ou 1."
        }

    conexao = sqlite3.connect(CAMINHO_BANCO)

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            UPDATE item
            SET ativo = ?
            WHERE id = ?
            """,
            (ativo, item_id)
        )

        if cursor.rowcount == 0:
            return {
                "sucesso": False,
                "erro": "Item não encontrado."
            }

        conexao.commit()

        return {
            "sucesso": True,
            "id": item_id,
            "ativo": ativo
        }

    finally:
        conexao.close()


def cadastrar_valor_item(item_id, valor, data_inicio_valor):
    """Cadastra um novo valor para um item.

    O valor fica registrado no histórico e não altera registros anteriores.
    """

    if valor < 0:
        return {
            "sucesso": False,
            "erro": "O valor do item não pode ser negativo."
        }

    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                id,
                nome,
                ativo
            FROM item
            WHERE id = ?
            """,
            (item_id,)
        )

        item = cursor.fetchone()

        if item is None:
            return {
                "sucesso": False,
                "erro": "Item não encontrado."
            }

        cursor.execute(
            """
            INSERT INTO item_valor (
                item_id,
                valor,
                data_inicio_valor
            )
            VALUES (?, ?, ?)
            """,
            (
                item_id,
                valor,
                data_inicio_valor
            )
        )

        item_valor_id = cursor.lastrowid

        conexao.commit()

        return {
            "sucesso": True,
            "id": item_valor_id,
            "item_id": item_id,
            "valor": valor,
            "data_inicio_valor": data_inicio_valor
        }

    finally:
        conexao.close()


def buscar_valor_item(item_id, data_referencia=None):
    """Busca o valor vigente do item em uma determinada data.

    Se nenhuma data for informada, utiliza a data atual do sistema.
    """

    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    try:
        cursor = conexao.cursor()

        if data_referencia is None:
            cursor.execute(
                """
                SELECT
                    id,
                    item_id,
                    valor,
                    data_inicio_valor,
                    ativo
                FROM item_valor
                WHERE item_id = ?
                  AND ativo = 1
                ORDER BY data_inicio_valor DESC, id DESC
                LIMIT 1
                """,
                (item_id,)
            )
        else:
            cursor.execute(
                """
                SELECT
                    id,
                    item_id,
                    valor,
                    data_inicio_valor,
                    ativo
                FROM item_valor
                WHERE item_id = ?
                  AND ativo = 1
                  AND data_inicio_valor <= ?
                ORDER BY data_inicio_valor DESC, id DESC
                LIMIT 1
                """,
                (
                    item_id,
                    data_referencia
                )
            )

        valor = cursor.fetchone()

        if valor is None:
            return {
                "sucesso": False,
                "erro": "Não existe valor cadastrado para o item na data informada."
            }

        return {
            "sucesso": True,
            **dict(valor)
        }

    finally:
        conexao.close()


def listar_valores_item(item_id, apenas_ativos=True):
    """Lista o histórico de valores de um item."""

    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    try:
        cursor = conexao.cursor()

        if apenas_ativos:
            cursor.execute(
                """
                SELECT
                    id,
                    item_id,
                    valor,
                    data_inicio_valor,
                    ativo
                FROM item_valor
                WHERE item_id = ?
                  AND ativo = 1
                ORDER BY data_inicio_valor DESC, id DESC
                """,
                (item_id,)
            )
        else:
            cursor.execute(
                """
                SELECT
                    id,
                    item_id,
                    valor,
                    data_inicio_valor,
                    ativo
                FROM item_valor
                WHERE item_id = ?
                ORDER BY data_inicio_valor DESC, id DESC
                """,
                (item_id,)
            )

        valores = cursor.fetchall()

        return [dict(valor) for valor in valores]

    finally:
        conexao.close()


def alterar_status_valor(item_valor_id, ativo):
    """Ativa ou desativa um registro de valor."""

    if ativo not in (0, 1):
        return {
            "sucesso": False,
            "erro": "O status deve ser 0 ou 1."
        }

    conexao = sqlite3.connect(CAMINHO_BANCO)

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            UPDATE item_valor
            SET ativo = ?
            WHERE id = ?
            """,
            (
                ativo,
                item_valor_id
            )
        )

        if cursor.rowcount == 0:
            return {
                "sucesso": False,
                "erro": "Valor do item não encontrado."
            }

        conexao.commit()

        return {
            "sucesso": True,
            "id": item_valor_id,
            "ativo": ativo
        }

    finally:
        conexao.close()
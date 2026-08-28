import sqlite3
from datetime import date, datetime

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
            INSERT INTO itens (
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
            FROM itens
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

        sql = """SELECT i.id, i.nome, i.codigo_barras, i.descricao, i.categoria,
                        i.unidade_medida, i.estoque_atual, i.estoque_minimo, i.ativo,
                        (SELECT iv.valor FROM itens_valores iv WHERE iv.item_id=i.id
                         AND iv.ativo=1 AND iv.data_inicio_valor<=date('now','localtime')
                         ORDER BY iv.data_inicio_valor DESC, iv.id DESC LIMIT 1) AS valor_atual
                 FROM itens i"""
        if apenas_ativos:
            sql += " WHERE i.ativo = 1"
        sql += " ORDER BY i.nome"
        cursor.execute(sql)

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
            UPDATE itens
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
            FROM itens
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
            INSERT INTO itens_valores (
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
                FROM itens_valores
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
                FROM itens_valores
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
                FROM itens_valores
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
                FROM itens_valores
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
            UPDATE itens_valores
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


def cadastrar_produto(nome, valor, estoque_inicial=0, estoque_minimo=0,
                      codigo_barras=None, descricao=None, categoria=None,
                      unidade_medida="UN", ativo=1, data_inicio_valor=None):
    """Cadastra produto, preço inicial e estoque em uma única transação."""
    nome = str(nome or "").strip()
    codigo_barras = str(codigo_barras or "").strip() or None
    descricao = str(descricao or "").strip() or None
    categoria = str(categoria or "").strip() or None
    unidade_medida = str(unidade_medida or "UN").strip().upper()
    data_inicio_valor = data_inicio_valor or date.today().isoformat()
    if not nome:
        return {"sucesso": False, "erro": "O nome do produto é obrigatório."}
    try:
        valor = round(float(valor), 2)
        estoque_inicial = int(estoque_inicial)
        estoque_minimo = int(estoque_minimo)
        ativo = int(ativo)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Preço, estoque e status devem ser numéricos."}
    if valor <= 0:
        return {"sucesso": False, "erro": "O preço deve ser maior que zero."}
    if estoque_inicial < 0 or estoque_minimo < 0:
        return {"sucesso": False, "erro": "Os estoques não podem ser negativos."}
    if ativo not in (0, 1):
        return {"sucesso": False, "erro": "Status inválido."}
    if not unidade_medida:
        return {"sucesso": False, "erro": "A unidade de medida é obrigatória."}
    try:
        if datetime.strptime(data_inicio_valor, "%Y-%m-%d").strftime("%Y-%m-%d") != data_inicio_valor:
            raise ValueError
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "A data inicial do preço é inválida."}

    conexao = sqlite3.connect(CAMINHO_BANCO)
    try:
        conexao.execute("BEGIN")
        cursor = conexao.execute(
            """INSERT INTO itens
               (nome,codigo_barras,descricao,categoria,unidade_medida,estoque_atual,estoque_minimo,ativo)
               VALUES (?,?,?,?,?,?,?,?)""",
            (nome, codigo_barras, descricao, categoria, unidade_medida,
             estoque_inicial, estoque_minimo, ativo),
        )
        item_id = cursor.lastrowid
        preco = conexao.execute(
            "INSERT INTO itens_valores (item_id,valor,data_inicio_valor) VALUES (?,?,?)",
            (item_id, valor, data_inicio_valor),
        )
        conexao.commit()
        return {"sucesso": True, "id": item_id, "item_valor_id": preco.lastrowid,
                "nome": nome, "valor": valor, "estoque_atual": estoque_inicial}
    except sqlite3.IntegrityError as erro:
        conexao.rollback()
        mensagem = "Já existe um produto com esse nome."
        if codigo_barras and "codigo_barras" in str(erro):
            mensagem = "Já existe um produto com esse código de barras."
        return {"sucesso": False, "erro": mensagem}
    finally:
        conexao.close()

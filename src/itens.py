import sqlite3
import unicodedata
from datetime import date, datetime

from src.banco import CAMINHO_BANCO


def _eh_servico(categoria):
    texto = unicodedata.normalize("NFKD", str(categoria or ""))
    return "".join(char for char in texto if not unicodedata.combining(char)).strip().upper() in {"SERVICO", "SERVICOS"}


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
                        CASE WHEN i.ativo=0 THEN 'INATIVO'
                             WHEN UPPER(i.categoria) IN ('SERVIÇO','SERVIÇOS','SERVICO','SERVICOS') THEN 'NÃO SE APLICA'
                             WHEN i.estoque_atual=0 THEN 'SEM ESTOQUE'
                             WHEN i.estoque_atual<=i.estoque_minimo THEN 'REPOR'
                             ELSE 'OK' END AS situacao_estoque,
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

    try:
        valor = round(float(valor), 2)
        if datetime.strptime(data_inicio_valor, "%Y-%m-%d").strftime("%Y-%m-%d") != data_inicio_valor:
            raise ValueError
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Preço ou data inicial inválida."}

    if valor <= 0:
        return {
            "sucesso": False,
            "erro": "O valor do item deve ser maior que zero."
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
    if _eh_servico(categoria):
        estoque_inicial = 0
        estoque_minimo = 0
        unidade_medida = "SERV"
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
        if estoque_inicial:
            conexao.execute(
                """INSERT INTO movimentacoes_estoque
                   (item_id,quantidade_anterior,quantidade_movimentada,quantidade_atual,
                    motivo,data_movimentacao,tipo)
                   VALUES(?,0,?,?,?,?,'SALDO_INICIAL')""",
                (item_id, estoque_inicial, estoque_inicial, "Estoque inicial do cadastro", data_inicio_valor),
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


def editar_produto(item_id, nome, codigo_barras=None, descricao=None, categoria=None,
                   unidade_medida="UN", estoque_minimo=0, ativo=1):
    nome = str(nome or "").strip()
    codigo_barras = str(codigo_barras or "").strip() or None
    descricao = str(descricao or "").strip() or None
    categoria = str(categoria or "").strip() or None
    unidade_medida = str(unidade_medida or "").strip().upper()
    try:
        estoque_minimo = int(estoque_minimo)
        ativo = int(ativo)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Estoque mínimo ou situação inválida."}
    if not nome or not unidade_medida:
        return {"sucesso": False, "erro": "Nome e unidade de medida são obrigatórios."}
    if estoque_minimo < 0 or ativo not in (0, 1):
        return {"sucesso": False, "erro": "Estoque mínimo ou situação inválida."}
    if _eh_servico(categoria):
        estoque_minimo = 0
        unidade_medida = "SERV"
    conexao = sqlite3.connect(CAMINHO_BANCO)
    try:
        cursor = conexao.execute(
            """UPDATE itens SET nome=?,codigo_barras=?,descricao=?,categoria=?,
               unidade_medida=?,estoque_minimo=?,estoque_atual=CASE WHEN ? THEN 0 ELSE estoque_atual END,ativo=? WHERE id=?""",
            (nome, codigo_barras, descricao, categoria, unidade_medida, estoque_minimo, int(_eh_servico(categoria)), ativo, item_id),
        )
        if cursor.rowcount == 0:
            return {"sucesso": False, "erro": "Produto não encontrado."}
        conexao.commit()
        return {"sucesso": True, "id": item_id, "nome": nome, "ativo": ativo}
    except sqlite3.IntegrityError as erro:
        mensagem = "Já existe um produto com esse nome."
        if codigo_barras and "codigo_barras" in str(erro):
            mensagem = "Já existe um produto com esse código de barras."
        return {"sucesso": False, "erro": mensagem}
    finally:
        conexao.close()


def ajustar_estoque(item_id, quantidade, motivo, data_movimentacao=None, tipo=None,
                    custo_unitario=None, fornecedor=None, documento=None,
                    lote=None, data_validade=None):
    motivo = str(motivo or "").strip()
    data_movimentacao = data_movimentacao or date.today().isoformat()
    tipo_informado = str(tipo or "").strip().upper()
    fornecedor = str(fornecedor or "").strip() or None
    documento = str(documento or "").strip() or None
    lote = str(lote or "").strip() or None
    data_validade = str(data_validade or "").strip() or None
    try:
        quantidade = int(quantidade)
        if datetime.strptime(data_movimentacao, "%Y-%m-%d").strftime("%Y-%m-%d") != data_movimentacao:
            raise ValueError
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Quantidade ou data inválida."}
    if quantidade == 0:
        return {"sucesso": False, "erro": "A quantidade do ajuste não pode ser zero."}
    if tipo_informado not in ("", "ENTRADA", "SAIDA"):
        return {"sucesso": False, "erro": "O tipo deve ser ENTRADA ou SAIDA."}
    if tipo_informado and quantidade < 0:
        return {"sucesso": False, "erro": "Informe a quantidade como um número positivo."}
    quantidade_movimentada = quantidade
    tipo_movimentacao = "AJUSTE"
    if tipo_informado == "ENTRADA":
        quantidade_movimentada = abs(quantidade)
        tipo_movimentacao = "ENTRADA"
    elif tipo_informado == "SAIDA":
        quantidade_movimentada = -abs(quantidade)
        tipo_movimentacao = "SAIDA"
    if not motivo:
        return {"sucesso": False, "erro": "Informe o motivo do ajuste de estoque."}
    try:
        custo_unitario = None if custo_unitario in (None, "") else round(float(custo_unitario), 2)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "O custo unitário é inválido."}
    if custo_unitario is not None and custo_unitario < 0:
        return {"sucesso": False, "erro": "O custo unitário não pode ser negativo."}
    if data_validade:
        try:
            if datetime.strptime(data_validade, "%Y-%m-%d").strftime("%Y-%m-%d") != data_validade:
                raise ValueError
        except ValueError:
            return {"sucesso": False, "erro": "A data de validade é inválida."}
    conexao = sqlite3.connect(CAMINHO_BANCO)
    try:
        conexao.execute("BEGIN IMMEDIATE")
        item = conexao.execute("SELECT estoque_atual,categoria FROM itens WHERE id=?", (item_id,)).fetchone()
        if not item:
            return {"sucesso": False, "erro": "Produto não encontrado."}
        if _eh_servico(item[1]):
            return {"sucesso": False, "erro": "Serviços não possuem controle de estoque."}
        anterior = item[0]
        atual = anterior + quantidade_movimentada
        if atual < 0:
            return {"sucesso": False, "erro": "O ajuste deixaria o estoque negativo."}
        conexao.execute("UPDATE itens SET estoque_atual=? WHERE id=?", (atual, item_id))
        cursor = conexao.execute(
            """INSERT INTO movimentacoes_estoque
               (item_id,quantidade_anterior,quantidade_movimentada,quantidade_atual,
                motivo,data_movimentacao,tipo,custo_unitario,fornecedor,documento,lote,data_validade)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (item_id, anterior, quantidade_movimentada, atual, motivo, data_movimentacao,
             tipo_movimentacao, custo_unitario, fornecedor, documento, lote, data_validade),
        )
        conexao.commit()
        return {"sucesso": True, "id": cursor.lastrowid, "item_id": item_id,
                "tipo": tipo_movimentacao, "estoque_atual": atual}
    finally:
        conexao.close()


def listar_movimentacoes_estoque(item_id):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    try:
        return [dict(linha) for linha in conexao.execute(
            """SELECT id,item_id,quantidade_anterior,quantidade_movimentada,
                      quantidade_atual,motivo,data_movimentacao,tipo,venda_id,
                      custo_unitario,fornecedor,documento,lote,data_validade
               FROM movimentacoes_estoque WHERE item_id=?
               ORDER BY data_movimentacao DESC,id DESC""",
            (item_id,),
        )]
    finally:
        conexao.close()

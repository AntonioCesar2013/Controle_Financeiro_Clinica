"""Operações da cantina vinculadas às carteiras dos residentes."""

from datetime import date, datetime
import sqlite3

from src.banco import conectar
from src.internacoes import sincronizar_status_residentes


def _data_valida(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").strftime("%Y-%m-%d") == valor
    except (TypeError, ValueError):
        return False


def criar_carteira(residente_id, saldo_inicial=0):
    sincronizar_status_residentes()
    try:
        saldo_inicial = round(float(saldo_inicial), 2)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "O saldo inicial deve ser numérico."}
    if saldo_inicial < 0:
        return {"sucesso": False, "erro": "O saldo inicial não pode ser negativo."}
    conn = conectar()
    try:
        residente = conn.execute("SELECT id, ativo FROM residentes WHERE id=?", (residente_id,)).fetchone()
        if not residente:
            return {"sucesso": False, "erro": "Residente não encontrado."}
        if not residente[1]:
            return {"sucesso": False, "erro": "O residente está inativo."}
        cursor = conn.execute("INSERT INTO carteiras (residente_id, saldo) VALUES (?, ?)", (residente_id, saldo_inicial))
        carteira_id = cursor.lastrowid
        if saldo_inicial:
            conn.execute(
                "INSERT INTO movimentacoes_carteira (carteira_id, tipo, quantidade, valor_total, data_movimentacao) VALUES (?, 'CREDITO', 1, ?, ?)",
                (carteira_id, saldo_inicial, date.today().isoformat()),
            )
        conn.commit()
        return {"sucesso": True, "id": carteira_id, "saldo": saldo_inicial}
    except sqlite3.IntegrityError:
        conn.rollback()
        return {"sucesso": False, "erro": "O residente já possui carteira."}
    finally:
        conn.close()


def adicionar_credito(carteira_id, valor, data_movimentacao=None):
    try:
        valor = round(float(valor), 2)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "O valor deve ser numérico."}
    data_movimentacao = data_movimentacao or date.today().isoformat()
    if valor <= 0:
        return {"sucesso": False, "erro": "O valor deve ser maior que zero."}
    if not _data_valida(data_movimentacao):
        return {"sucesso": False, "erro": "Data inválida. Use YYYY-MM-DD."}
    conn = conectar()
    try:
        conn.execute("BEGIN IMMEDIATE")
        carteira = conn.execute("SELECT id, ativo FROM carteiras WHERE id=?", (carteira_id,)).fetchone()
        if not carteira:
            return {"sucesso": False, "erro": "Carteira não encontrada."}
        if not carteira[1]:
            return {"sucesso": False, "erro": "A carteira está inativa."}
        conn.execute("UPDATE carteiras SET saldo=ROUND(saldo + ?, 2) WHERE id=?", (valor, carteira_id))
        conn.execute(
            "INSERT INTO movimentacoes_carteira (carteira_id, tipo, quantidade, valor_total, data_movimentacao) VALUES (?, 'CREDITO', 1, ?, ?)",
            (carteira_id, valor, data_movimentacao),
        )
        saldo = conn.execute("SELECT saldo FROM carteiras WHERE id=?", (carteira_id,)).fetchone()[0]
        conn.commit()
        return {"sucesso": True, "carteira_id": carteira_id, "saldo": saldo}
    finally:
        conn.close()


def registrar_venda(carteira_id, item_id, quantidade=1, data_movimentacao=None):
    sincronizar_status_residentes()
    try:
        quantidade = int(quantidade)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "A quantidade deve ser um número inteiro."}
    data_movimentacao = data_movimentacao or date.today().isoformat()
    if quantidade <= 0:
        return {"sucesso": False, "erro": "A quantidade deve ser maior que zero."}
    if not _data_valida(data_movimentacao):
        return {"sucesso": False, "erro": "Data inválida. Use YYYY-MM-DD."}

    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        carteira = conn.execute(
            """SELECT c.id, c.saldo, c.ativo, r.nome, r.ativo AS residente_ativo
               FROM carteiras c JOIN residentes r ON r.id=c.residente_id WHERE c.id=?""",
            (carteira_id,),
        ).fetchone()
        if not carteira:
            return {"sucesso": False, "erro": "Carteira não encontrada."}
        if not carteira["ativo"] or not carteira["residente_ativo"]:
            return {"sucesso": False, "erro": "Carteira ou residente inativo."}
        item = conn.execute("SELECT id, nome, ativo FROM itens WHERE id=?", (item_id,)).fetchone()
        if not item:
            return {"sucesso": False, "erro": "Item não encontrado."}
        if not item["ativo"]:
            return {"sucesso": False, "erro": "O item está inativo."}
        valor = conn.execute(
            """SELECT id, valor FROM itens_valores
               WHERE item_id=? AND ativo=1 AND data_inicio_valor<=?
               ORDER BY data_inicio_valor DESC, id DESC LIMIT 1""",
            (item_id, data_movimentacao),
        ).fetchone()
        if not valor:
            return {"sucesso": False, "erro": "O item não possui preço vigente para a data da venda."}
        total = round(valor["valor"] * quantidade, 2)
        estoque = conn.execute(
            "UPDATE itens SET estoque_atual=estoque_atual-? WHERE id=? AND estoque_atual>=?",
            (quantidade, item_id, quantidade),
        )
        if estoque.rowcount == 0:
            return {"sucesso": False, "erro": "Estoque insuficiente para esta venda."}
        cursor = conn.execute(
            "UPDATE carteiras SET saldo=ROUND(saldo - ?, 2) WHERE id=? AND saldo>=?",
            (total, carteira_id, total),
        )
        if cursor.rowcount == 0:
            return {"sucesso": False, "erro": "Saldo insuficiente na carteira."}
        cursor = conn.execute(
            """INSERT INTO movimentacoes_carteira
               (carteira_id, tipo, item_id, quantidade, item_valor_id, valor_total, data_movimentacao)
               VALUES (?, 'COMPRA_CANTINA', ?, ?, ?, ?, ?)""",
            (carteira_id, item_id, quantidade, valor["id"], total, data_movimentacao),
        )
        saldo = conn.execute("SELECT saldo FROM carteiras WHERE id=?", (carteira_id,)).fetchone()[0]
        conn.commit()
        return {"sucesso": True, "id": cursor.lastrowid, "residente": carteira["nome"],
                "item": item["nome"], "quantidade": quantidade, "valor_total": total, "saldo": saldo}
    except sqlite3.Error as erro:
        conn.rollback()
        return {"sucesso": False, "erro": f"Erro no banco de dados: {erro}"}
    finally:
        conn.close()


def consultar_cantina():
    sincronizar_status_residentes()
    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        carteiras = [dict(x) for x in conn.execute(
            """SELECT c.id, c.residente_id, r.nome AS residente_nome, c.saldo
               FROM carteiras c JOIN residentes r ON r.id=c.residente_id
               WHERE c.ativo=1 AND r.ativo=1 ORDER BY r.nome"""
        )]
        itens = [dict(x) for x in conn.execute(
            """SELECT i.id, i.nome, i.categoria, i.unidade_medida, i.estoque_atual,
                      iv.id AS item_valor_id, iv.valor
               FROM itens i JOIN itens_valores iv ON iv.id=(
                   SELECT iv2.id FROM itens_valores iv2 WHERE iv2.item_id=i.id
                   AND iv2.ativo=1 AND iv2.data_inicio_valor<=date('now','localtime')
                   ORDER BY iv2.data_inicio_valor DESC, iv2.id DESC LIMIT 1)
               WHERE i.ativo=1 AND i.estoque_atual>0 ORDER BY i.nome"""
        )]
        vendas = [dict(x) for x in conn.execute(
            """SELECT m.id, m.data_movimentacao, r.nome AS residente_nome,
                      i.nome AS item_nome, m.quantidade, m.valor_total
               FROM movimentacoes_carteira m JOIN carteiras c ON c.id=m.carteira_id
               JOIN residentes r ON r.id=c.residente_id JOIN itens i ON i.id=m.item_id
               WHERE m.tipo='COMPRA_CANTINA' ORDER BY m.data_movimentacao DESC, m.id DESC LIMIT 100"""
        )]
        return {"carteiras": carteiras, "itens": itens, "vendas": vendas}
    finally:
        conn.close()


def consultar_carteira(carteira_id):
    """Retorna saldo e histórico de compras da carteira selecionada."""
    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        carteira = conn.execute(
            """SELECT c.id, c.residente_id, r.nome AS residente_nome, c.saldo, c.ativo
               FROM carteiras c JOIN residentes r ON r.id=c.residente_id
               WHERE c.id=?""",
            (carteira_id,),
        ).fetchone()
        if not carteira:
            return {"sucesso": False, "erro": "Carteira não encontrada."}
        compras = [dict(x) for x in conn.execute(
            """SELECT m.id, m.data_movimentacao, i.nome AS item_nome,
                      m.quantidade, iv.valor AS valor_unitario, m.valor_total
               FROM movimentacoes_carteira m
               JOIN itens i ON i.id=m.item_id
               JOIN itens_valores iv ON iv.id=m.item_valor_id
               WHERE m.carteira_id=? AND m.tipo='COMPRA_CANTINA'
               ORDER BY m.data_movimentacao DESC, m.id DESC""",
            (carteira_id,),
        )]
        return {"sucesso": True, "carteira": dict(carteira), "compras": compras}
    finally:
        conn.close()

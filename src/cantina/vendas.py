from src.financeiro.moeda import validar_centavos
"""Operações da cantina vinculadas às carteiras dos residentes."""

from datetime import date, datetime
import sqlite3
import unicodedata

from src.infraestrutura.banco import conectar
from src.cadastros.internacoes import sincronizar_status_residentes


def _eh_servico(categoria):
    texto = unicodedata.normalize("NFKD", str(categoria or ""))
    return "".join(char for char in texto if not unicodedata.combining(char)).strip().upper() in {"SERVICO", "SERVICOS"}


def _data_valida(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").strftime("%Y-%m-%d") == valor
    except (TypeError, ValueError):
        return False


def criar_carteira(residente_id, saldo_inicial=0):
    sincronizar_status_residentes()
    try:
        saldo_inicial = validar_centavos(saldo_inicial)
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
        valor = validar_centavos(valor)
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
        conn.execute("UPDATE carteiras SET saldo=saldo + ? WHERE id=?", (valor, carteira_id))
        conn.execute(
            "INSERT INTO movimentacoes_carteira (carteira_id, tipo, quantidade, valor_total, data_movimentacao) VALUES (?, 'CREDITO', 1, ?, ?)",
            (carteira_id, valor, data_movimentacao),
        )
        saldo = conn.execute("SELECT saldo FROM carteiras WHERE id=?", (carteira_id,)).fetchone()[0]
        conn.commit()
        return {"sucesso": True, "carteira_id": carteira_id, "saldo": saldo}
    finally:
        conn.close()


def alterar_status_carteira(carteira_id, ativo):
    try:
        ativo = int(ativo)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Situação da carteira inválida."}
    if ativo not in (0, 1):
        return {"sucesso": False, "erro": "Situação da carteira inválida."}
    conn = conectar()
    try:
        cursor = conn.execute("UPDATE carteiras SET ativo=? WHERE id=?", (ativo, carteira_id))
        if cursor.rowcount == 0:
            return {"sucesso": False, "erro": "Carteira não encontrada."}
        conn.commit()
        return {"sucesso": True, "id": carteira_id, "ativo": ativo}
    finally:
        conn.close()


def estornar_movimentacao(movimentacao_id, motivo=None):
    motivo = str(motivo or "Correção de lançamento").strip()
    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        movimento = conn.execute(
            """SELECT id,carteira_id,tipo,item_id,quantidade,valor_total,estornada,venda_id
               FROM movimentacoes_carteira WHERE id=?""",
            (movimentacao_id,),
        ).fetchone()
        if not movimento:
            return {"sucesso": False, "erro": "Movimentação não encontrada."}
        if movimento["estornada"]:
            return {"sucesso": False, "erro": "A movimentação já foi estornada."}
        if movimento["venda_id"] is not None:
            return {
                "sucesso": False,
                "erro": "Esta movimentação pertence a um cupom. Estorne a venda completa na Cantina.",
            }
        if movimento["tipo"] == "CREDITO":
            saldo = conn.execute("SELECT saldo FROM carteiras WHERE id=?", (movimento["carteira_id"],)).fetchone()[0]
            if saldo < movimento["valor_total"]:
                return {"sucesso": False, "erro": "O saldo atual não permite estornar este crédito."}
            conn.execute(
                "UPDATE carteiras SET saldo=saldo-? WHERE id=?",
                (movimento["valor_total"], movimento["carteira_id"]),
            )
        elif movimento["tipo"] == "COMPRA_CANTINA":
            conn.execute(
                "UPDATE carteiras SET saldo=saldo+? WHERE id=?",
                (movimento["valor_total"], movimento["carteira_id"]),
            )
            item = conn.execute(
                "SELECT estoque_atual,categoria FROM itens WHERE id=?", (movimento["item_id"],)
            ).fetchone()
            if not _eh_servico(item["categoria"]):
                conn.execute(
                    "UPDATE itens SET estoque_atual=estoque_atual+? WHERE id=?",
                    (movimento["quantidade"], movimento["item_id"]),
                )
                conn.execute(
                    """INSERT INTO movimentacoes_estoque
                       (item_id,quantidade_anterior,quantidade_movimentada,quantidade_atual,
                        motivo,data_movimentacao,tipo)
                       VALUES(?,?,?,?,?,?,'ESTORNO')""",
                    (movimento["item_id"], item["estoque_atual"], movimento["quantidade"],
                     item["estoque_atual"] + movimento["quantidade"], motivo, date.today().isoformat()),
                )
        else:
            return {"sucesso": False, "erro": "Tipo de movimentação não pode ser estornado."}
        conn.execute(
            """UPDATE movimentacoes_carteira
               SET estornada=1,estornada_em=?,motivo_estorno=? WHERE id=?""",
            (datetime.now().isoformat(timespec="seconds"), motivo, movimentacao_id),
        )
        saldo_atual = conn.execute("SELECT saldo FROM carteiras WHERE id=?", (movimento["carteira_id"],)).fetchone()[0]
        conn.commit()
        return {"sucesso": True, "id": movimentacao_id, "carteira_id": movimento["carteira_id"], "saldo": saldo_atual}
    except sqlite3.Error as erro:
        conn.rollback()
        return {"sucesso": False, "erro": f"Erro no banco de dados: {erro}"}
    finally:
        conn.close()


def corrigir_credito(movimentacao_id, novo_valor, data_movimentacao=None, motivo=None):
    try:
        novo_valor = validar_centavos(novo_valor)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "O novo valor deve ser numérico."}
    if novo_valor <= 0:
        return {"sucesso": False, "erro": "O novo valor deve ser maior que zero."}
    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        movimento = conn.execute(
            """SELECT m.carteira_id,m.tipo,m.data_movimentacao,m.valor_total,m.estornada,
                      c.saldo,c.ativo FROM movimentacoes_carteira m
               JOIN carteiras c ON c.id=m.carteira_id WHERE m.id=?""",
            (movimentacao_id,),
        ).fetchone()
        if not movimento or movimento["tipo"] != "CREDITO":
            return {"sucesso": False, "erro": "Crédito não encontrado."}
        if movimento["estornada"]:
            return {"sucesso": False, "erro": "O crédito já foi estornado."}
        if not movimento["ativo"]:
            return {"sucesso": False, "erro": "A carteira está inativa."}
        data_movimentacao = data_movimentacao or movimento["data_movimentacao"]
        if not _data_valida(data_movimentacao):
            return {"sucesso": False, "erro": "Data inválida. Use YYYY-MM-DD."}
        saldo_sem_original = movimento["saldo"] - movimento["valor_total"]
        conn.execute(
            "UPDATE carteiras SET saldo=? WHERE id=?",
            (saldo_sem_original + novo_valor, movimento["carteira_id"]),
        )
        conn.execute(
            """UPDATE movimentacoes_carteira SET estornada=1,estornada_em=?,motivo_estorno=?
               WHERE id=?""",
            (datetime.now().isoformat(timespec="seconds"), str(motivo or "Crédito corrigido").strip(), movimentacao_id),
        )
        cursor = conn.execute(
            """INSERT INTO movimentacoes_carteira
               (carteira_id,tipo,quantidade,valor_total,data_movimentacao)
               VALUES(?,'CREDITO',1,?,?)""",
            (movimento["carteira_id"], novo_valor, data_movimentacao),
        )
        saldo = conn.execute("SELECT saldo FROM carteiras WHERE id=?", (movimento["carteira_id"],)).fetchone()[0]
        conn.commit()
        return {"sucesso": True, "id": cursor.lastrowid, "carteira_id": movimento["carteira_id"],
                "saldo": saldo, "movimentacao_estornada_id": movimentacao_id}
    except sqlite3.Error as erro:
        conn.rollback()
        return {"sucesso": False, "erro": f"Erro no banco de dados: {erro}"}
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
        item = conn.execute("SELECT id, nome, categoria, ativo, estoque_atual FROM itens WHERE id=?", (item_id,)).fetchone()
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
        total = valor["valor"] * quantidade
        if not _eh_servico(item["categoria"]):
            estoque = conn.execute(
                "UPDATE itens SET estoque_atual=estoque_atual-? WHERE id=? AND estoque_atual>=?",
                (quantidade, item_id, quantidade),
            )
            if estoque.rowcount == 0:
                return {"sucesso": False, "erro": "Estoque insuficiente para esta venda."}
        conn.execute(
            "UPDATE carteiras SET saldo=saldo - ? WHERE id=?",
            (total, carteira_id),
        )
        cursor = conn.execute(
            """INSERT INTO movimentacoes_carteira
               (carteira_id, tipo, item_id, quantidade, item_valor_id, valor_total, data_movimentacao)
               VALUES (?, 'COMPRA_CANTINA', ?, ?, ?, ?, ?)""",
            (carteira_id, item_id, quantidade, valor["id"], total, data_movimentacao),
        )
        if not _eh_servico(item["categoria"]):
            conn.execute(
                """INSERT INTO movimentacoes_estoque
                   (item_id,quantidade_anterior,quantidade_movimentada,quantidade_atual,
                    motivo,data_movimentacao,tipo)
                   VALUES(?,?,?,?,?,?,'VENDA')""",
                (item_id, item["estoque_atual"], -quantidade, item["estoque_atual"] - quantidade,
                 "Venda na Cantina", data_movimentacao),
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


def buscar_produto_codigo(codigo_barras, data_referencia=None):
    codigo_barras = str(codigo_barras or "").strip()
    data_referencia = data_referencia or date.today().isoformat()
    if not codigo_barras:
        return {"sucesso": False, "erro": "Leia ou informe um código de barras."}
    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        produto = conn.execute(
            """SELECT i.id,i.nome,i.codigo_barras,i.categoria,i.unidade_medida,
                      i.estoque_atual,i.ativo,iv.id AS item_valor_id,iv.valor
               FROM itens i LEFT JOIN itens_valores iv ON iv.id=(
                   SELECT iv2.id FROM itens_valores iv2 WHERE iv2.item_id=i.id
                   AND iv2.ativo=1 AND iv2.data_inicio_valor<=?
                   ORDER BY iv2.data_inicio_valor DESC,iv2.id DESC LIMIT 1)
               WHERE i.codigo_barras=?""",
            (data_referencia, codigo_barras),
        ).fetchone()
        if not produto:
            return {"sucesso": False, "erro": "Código de barras não cadastrado."}
        if not produto["ativo"]:
            return {"sucesso": False, "erro": "O produto está inativo."}
        if produto["item_valor_id"] is None:
            return {"sucesso": False, "erro": "O produto não possui preço vigente."}
        if not _eh_servico(produto["categoria"]) and produto["estoque_atual"] <= 0:
            return {"sucesso": False, "erro": "O produto está sem estoque."}
        return {"sucesso": True, **dict(produto)}
    finally:
        conn.close()


def registrar_compra(carteira_id, produtos, data_movimentacao=None):
    sincronizar_status_residentes()
    data_movimentacao = data_movimentacao or date.today().isoformat()
    if not _data_valida(data_movimentacao):
        return {"sucesso": False, "erro": "Data inválida. Use YYYY-MM-DD."}
    if not isinstance(produtos, list) or not produtos:
        return {"sucesso": False, "erro": "Adicione pelo menos um produto ao carrinho."}
    agrupados = {}
    try:
        for produto in produtos:
            item_id = int(produto.get("item_id"))
            quantidade = int(produto.get("quantidade", 1))
            if quantidade <= 0:
                raise ValueError
            agrupados[item_id] = agrupados.get(item_id, 0) + quantidade
    except (AttributeError, TypeError, ValueError):
        return {"sucesso": False, "erro": "Há um produto ou quantidade inválida no carrinho."}

    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        carteira = conn.execute(
            """SELECT c.id,c.saldo,c.ativo,r.nome,r.ativo AS residente_ativo
               FROM carteiras c JOIN residentes r ON r.id=c.residente_id WHERE c.id=?""",
            (carteira_id,),
        ).fetchone()
        if not carteira:
            return {"sucesso": False, "erro": "Carteira não encontrada."}
        if not carteira["ativo"] or not carteira["residente_ativo"]:
            return {"sucesso": False, "erro": "Carteira ou residente inativo."}

        itens_venda = []
        total_venda = 0
        for item_id, quantidade in agrupados.items():
            item = conn.execute(
                """SELECT i.id,i.nome,i.categoria,i.ativo,i.estoque_atual,
                          iv.id AS item_valor_id,iv.valor
                   FROM itens i LEFT JOIN itens_valores iv ON iv.id=(
                       SELECT iv2.id FROM itens_valores iv2 WHERE iv2.item_id=i.id
                       AND iv2.ativo=1 AND iv2.data_inicio_valor<=?
                       ORDER BY iv2.data_inicio_valor DESC,iv2.id DESC LIMIT 1)
                   WHERE i.id=?""",
                (data_movimentacao, item_id),
            ).fetchone()
            if not item:
                return {"sucesso": False, "erro": "Um produto do carrinho não foi encontrado."}
            if not item["ativo"]:
                return {"sucesso": False, "erro": f"O produto {item['nome']} está inativo."}
            if item["item_valor_id"] is None:
                return {"sucesso": False, "erro": f"O produto {item['nome']} não possui preço vigente."}
            if not _eh_servico(item["categoria"]) and item["estoque_atual"] < quantidade:
                return {"sucesso": False, "erro": f"Estoque insuficiente para {item['nome']}."}
            subtotal = item["valor"] * quantidade
            total_venda = total_venda + subtotal
            itens_venda.append({**dict(item), "quantidade": quantidade, "subtotal": subtotal})
        venda = conn.execute(
            """INSERT INTO vendas_cantina(carteira_id,data_movimentacao,valor_total)
               VALUES(?,?,?)""",
            (carteira_id, data_movimentacao, total_venda),
        )
        venda_id = venda.lastrowid
        movimento_ids = []
        for item in itens_venda:
            if not _eh_servico(item["categoria"]):
                estoque = conn.execute(
                    "UPDATE itens SET estoque_atual=estoque_atual-? WHERE id=? AND estoque_atual>=?",
                    (item["quantidade"], item["id"], item["quantidade"]),
                )
                if estoque.rowcount == 0:
                    raise sqlite3.IntegrityError(f"Estoque alterado durante a venda de {item['nome']}.")
                conn.execute(
                    """INSERT INTO movimentacoes_estoque
                       (item_id,quantidade_anterior,quantidade_movimentada,quantidade_atual,
                        motivo,data_movimentacao,tipo,venda_id)
                       VALUES(?,?,?,?,?,?,'VENDA',?)""",
                    (item["id"], item["estoque_atual"], -item["quantidade"],
                     item["estoque_atual"] - item["quantidade"],
                     f"Venda no cupom nº {venda_id}", data_movimentacao, venda_id),
                )
            conn.execute(
                """INSERT INTO vendas_cantina_itens
                   (venda_id,item_id,item_valor_id,quantidade,valor_unitario,valor_total)
                   VALUES(?,?,?,?,?,?)""",
                (venda_id, item["id"], item["item_valor_id"], item["quantidade"], item["valor"], item["subtotal"]),
            )
            movimento = conn.execute(
                """INSERT INTO movimentacoes_carteira
                   (carteira_id,tipo,item_id,quantidade,item_valor_id,valor_total,data_movimentacao,venda_id)
                   VALUES(?,'COMPRA_CANTINA',?,?,?,?,?,?)""",
                (carteira_id, item["id"], item["quantidade"], item["item_valor_id"], item["subtotal"], data_movimentacao, venda_id),
            )
            movimento_ids.append(movimento.lastrowid)
        conn.execute("UPDATE carteiras SET saldo=saldo-? WHERE id=?", (total_venda, carteira_id))
        saldo = conn.execute("SELECT saldo FROM carteiras WHERE id=?", (carteira_id,)).fetchone()[0]
        conn.commit()
        return {"sucesso": True, "id": venda_id, "residente": carteira["nome"],
                "valor_total": total_venda, "saldo": saldo, "quantidade_produtos": len(itens_venda),
                "quantidade_itens": sum(item["quantidade"] for item in itens_venda),
                "movimentacoes": movimento_ids}
    except sqlite3.Error as erro:
        conn.rollback()
        return {"sucesso": False, "erro": f"Não foi possível finalizar a compra: {erro}"}
    finally:
        conn.close()


def estornar_compra(venda_id, motivo=None):
    motivo = str(motivo or "Venda cancelada").strip()
    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        venda = conn.execute(
            "SELECT id,carteira_id,valor_total,status FROM vendas_cantina WHERE id=?",
            (venda_id,),
        ).fetchone()
        if not venda:
            return {"sucesso": False, "erro": "Venda não encontrada."}
        if venda["status"] == "ESTORNADA":
            return {"sucesso": False, "erro": "A venda já foi estornada."}
        itens_venda = conn.execute(
            """SELECT vi.item_id,vi.quantidade,i.estoque_atual,i.categoria
               FROM vendas_cantina_itens vi JOIN itens i ON i.id=vi.item_id
               WHERE vi.venda_id=?""", (venda_id,)
        ).fetchall()
        if not itens_venda:
            return {"sucesso": False, "erro": "A venda não possui itens registrados."}
        for item in itens_venda:
            if _eh_servico(item["categoria"]):
                continue
            conn.execute(
                "UPDATE itens SET estoque_atual=estoque_atual+? WHERE id=?",
                (item["quantidade"], item["item_id"]),
            )
            conn.execute(
                """INSERT INTO movimentacoes_estoque
                   (item_id,quantidade_anterior,quantidade_movimentada,quantidade_atual,
                    motivo,data_movimentacao,tipo,venda_id)
                   VALUES(?,?,?,?,?,?,'ESTORNO',?)""",
                (item["item_id"], item["estoque_atual"], item["quantidade"],
                 item["estoque_atual"] + item["quantidade"], motivo,
                 date.today().isoformat(), venda_id),
            )
        conn.execute(
            "UPDATE carteiras SET saldo=saldo+? WHERE id=?",
            (venda["valor_total"], venda["carteira_id"]),
        )
        agora = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            """UPDATE vendas_cantina SET status='ESTORNADA',estornada_em=?,motivo_estorno=?
               WHERE id=?""",
            (agora, motivo, venda_id),
        )
        conn.execute(
            """UPDATE movimentacoes_carteira SET estornada=1,estornada_em=?,motivo_estorno=?
               WHERE venda_id=?""",
            (agora, motivo, venda_id),
        )
        saldo = conn.execute("SELECT saldo FROM carteiras WHERE id=?", (venda["carteira_id"],)).fetchone()[0]
        conn.commit()
        return {"sucesso": True, "id": venda_id, "carteira_id": venda["carteira_id"], "saldo": saldo}
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
            """SELECT i.id, i.nome, i.codigo_barras, i.categoria, i.unidade_medida, i.estoque_atual,
                      iv.id AS item_valor_id, iv.valor
               FROM itens i JOIN itens_valores iv ON iv.id=(
                   SELECT iv2.id FROM itens_valores iv2 WHERE iv2.item_id=i.id
                   AND iv2.ativo=1 AND iv2.data_inicio_valor<=date('now','localtime')
                   ORDER BY iv2.data_inicio_valor DESC, iv2.id DESC LIMIT 1)
               WHERE i.ativo=1 AND (i.estoque_atual>0 OR UPPER(i.categoria) IN ('SERVIÇO','SERVIÇOS','SERVICO','SERVICOS')) ORDER BY i.nome"""
        )]
        vendas = [dict(x) for x in conn.execute(
            """SELECT v.id,v.data_movimentacao,r.nome AS residente_nome,
                      v.valor_total,v.status,COUNT(vi.id) AS produtos,
                      COALESCE(SUM(vi.quantidade),0) AS itens
               FROM vendas_cantina v JOIN carteiras c ON c.id=v.carteira_id
               JOIN residentes r ON r.id=c.residente_id
               LEFT JOIN vendas_cantina_itens vi ON vi.venda_id=v.id
               GROUP BY v.id ORDER BY v.data_movimentacao DESC,v.id DESC LIMIT 100"""
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
        movimentos = [dict(x) for x in conn.execute(
            """SELECT m.id,m.tipo,m.data_movimentacao,m.valor_total,m.estornada,
                      m.estornada_em,m.motivo_estorno,i.nome AS item_nome,m.quantidade
               FROM movimentacoes_carteira m
               LEFT JOIN itens i ON i.id=m.item_id
               WHERE m.carteira_id=?
               ORDER BY m.data_movimentacao DESC,m.id DESC""",
            (carteira_id,),
        )]
        compras = [dict(x) for x in conn.execute(
            """SELECT m.id, m.data_movimentacao, i.nome AS item_nome,
                      m.quantidade, iv.valor AS valor_unitario, m.valor_total,
                      m.estornada,m.estornada_em,m.motivo_estorno,m.venda_id
               FROM movimentacoes_carteira m
               JOIN itens i ON i.id=m.item_id
               JOIN itens_valores iv ON iv.id=m.item_valor_id
               WHERE m.carteira_id=? AND m.tipo='COMPRA_CANTINA'
               ORDER BY m.data_movimentacao DESC, m.id DESC""",
            (carteira_id,),
        )]
        creditos = [movimento for movimento in movimentos if movimento["tipo"] == "CREDITO"]
        return {"sucesso": True, "carteira": dict(carteira), "movimentacoes": movimentos,
                "creditos": creditos, "compras": compras}
    finally:
        conn.close()

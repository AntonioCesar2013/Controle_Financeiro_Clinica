"""Cadastro de pertences pessoais vinculados a um único residente."""
from contextlib import closing
from datetime import date

from src.infraestrutura.banco import conectar
from src.nucleo.validacao import inteiro


def _campos(nome, quantidade, descricao):
    nome = str(nome or "").strip() if isinstance(nome, (str, type(None))) else ""
    if not nome or len(nome) > 200:
        raise ValueError("Informe o nome do item pessoal (até 200 caracteres).")
    quantidade = inteiro(quantidade, "quantidade", 1)
    if descricao is not None and not isinstance(descricao, str):
        raise ValueError("A descrição do item deve ser um texto.")
    descricao = (descricao or "").strip() or None
    if descricao and len(descricao) > 2000:
        raise ValueError("A descrição do item deve ter até 2000 caracteres.")
    return nome, quantidade, descricao


def _data(valor, campo, obrigatoria=False):
    if valor in (None, ""):
        if obrigatoria:
            raise ValueError(f"Informe a {campo}.")
        return None
    try:
        if not isinstance(valor, str) or date.fromisoformat(valor).isoformat() != valor:
            raise ValueError
    except ValueError:
        raise ValueError(f"A {campo} deve ser uma data válida no formato AAAA-MM-DD.") from None
    if valor > date.today().isoformat():
        raise ValueError(f"A {campo} não pode ser futura.")
    return valor


def _validar_datas(entrada, retirada):
    if retirada and not entrada:
        raise ValueError("Informe a data de entrada antes de registrar a retirada.")
    if retirada and retirada < entrada:
        raise ValueError("A retirada não pode ocorrer antes da entrada no inventário.")


def listar(residente_id):
    residente_id = inteiro(residente_id, "residente_id", 1)
    with closing(conectar()) as conexao:
        if not conexao.execute("SELECT 1 FROM residentes WHERE id=?", (residente_id,)).fetchone():
            raise ValueError("Residente não encontrado.")
        cursor = conexao.execute(
            "SELECT id,residente_id,nome,quantidade,descricao,data_entrada,data_retirada,cadastrado_em,atualizado_em "
            "FROM itens_residentes WHERE residente_id=? ORDER BY id", (residente_id,)
        )
        colunas = [coluna[0] for coluna in cursor.description]
        return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]


def cadastrar(residente_id, nome, quantidade=1, descricao=None, data_entrada=None, data_retirada=None):
    residente_id = inteiro(residente_id, "residente_id", 1)
    nome, quantidade, descricao = _campos(nome, quantidade, descricao)
    entrada = _data(date.today().isoformat() if data_entrada is None else data_entrada,
                    "data de entrada", True)
    retirada = _data(data_retirada, "data de retirada")
    _validar_datas(entrada, retirada)
    with closing(conectar()) as conexao, conexao:
        conexao.execute("BEGIN IMMEDIATE")
        if not conexao.execute("SELECT 1 FROM residentes WHERE id=?", (residente_id,)).fetchone():
            raise ValueError("Residente não encontrado.")
        cursor = conexao.execute(
            "INSERT INTO itens_residentes(residente_id,nome,quantidade,descricao,data_entrada,data_retirada) VALUES(?,?,?,?,?,?)",
            (residente_id, nome, quantidade, descricao, entrada, retirada),
        )
        return {"sucesso": True, "id": cursor.lastrowid, "residente_id": residente_id}


def editar(item_id, nome, quantidade=1, descricao=None, data_entrada=None, data_retirada=None):
    item_id = inteiro(item_id, "id", 1)
    nome, quantidade, descricao = _campos(nome, quantidade, descricao)
    with closing(conectar()) as conexao, conexao:
        conexao.execute("BEGIN IMMEDIATE")
        atual = conexao.execute(
            "SELECT residente_id,data_entrada,data_retirada FROM itens_residentes WHERE id=?", (item_id,)
        ).fetchone()
        if not atual:
            raise ValueError("Item pessoal não encontrado.")
        entrada = _data(data_entrada, "data de entrada") if data_entrada is not None else atual[1]
        retirada = _data(data_retirada, "data de retirada") if data_retirada is not None else atual[2]
        _validar_datas(entrada, retirada)
        conexao.execute(
            "UPDATE itens_residentes SET nome=?,quantidade=?,descricao=?,data_entrada=?,data_retirada=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (nome, quantidade, descricao, entrada, retirada, item_id),
        )
        return {"sucesso": True, "id": item_id, "residente_id": atual[0]}

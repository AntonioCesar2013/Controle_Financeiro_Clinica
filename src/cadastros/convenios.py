import sqlite3

from src.infraestrutura.banco import conectar


def cadastrar_convenio(nome, valor_diaria, ativo=1):
    nome = str(nome or "").strip()
    try:
        valor_diaria = int(valor_diaria)
        ativo = 1 if int(ativo) else 0
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Informe um valor de diária válido."}
    if not nome:
        return {"sucesso": False, "erro": "O nome do convênio é obrigatório."}
    if valor_diaria < 0:
        return {"sucesso": False, "erro": "O valor da diária não pode ser negativo."}
    conexao = conectar()
    try:
        cursor = conexao.execute(
            "INSERT INTO convenios(nome,valor_diaria,ativo) VALUES(?,?,?)",
            (nome, valor_diaria, ativo),
        )
        conexao.commit()
        return {"sucesso": True, "id": cursor.lastrowid}
    except sqlite3.IntegrityError:
        return {"sucesso": False, "erro": "Já existe um convênio com esse nome."}
    finally:
        conexao.close()


def listar_convenios(apenas_ativos=False):
    conexao = conectar()
    conexao.row_factory = sqlite3.Row
    try:
        filtro = " WHERE ativo=1" if apenas_ativos else ""
        return [dict(linha) for linha in conexao.execute(
            f"SELECT id,nome,valor_diaria,ativo FROM convenios{filtro} ORDER BY nome"
        )]
    finally:
        conexao.close()

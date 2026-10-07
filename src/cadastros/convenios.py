import sqlite3

from src.infraestrutura.banco import conectar
from src.cadastros.booleanos import normalizar_booleano


def cadastrar_convenio(nome, valor_diaria, ativo=1):
    nome = str(nome or "").strip()
    try:
        valor_diaria = int(valor_diaria)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Informe um valor de diária válido."}
    try:
        ativo = normalizar_booleano(ativo, "ativo")
    except ValueError as erro:
        return {"sucesso": False, "erro": str(erro)}
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


def editar_convenio(convenio_id, nome, valor_diaria, ativo=1):
    nome = str(nome or "").strip()
    try:
        convenio_id, valor_diaria = int(convenio_id), int(valor_diaria)
        ativo = normalizar_booleano(ativo, "ativo")
    except (TypeError, ValueError) as erro:
        return {"sucesso": False, "erro": str(erro) or "Dados do convênio inválidos."}
    if not nome:
        return {"sucesso": False, "erro": "O nome do convênio é obrigatório."}
    if valor_diaria < 0:
        return {"sucesso": False, "erro": "O valor da diária não pode ser negativo."}
    conexao = conectar()
    try:
        if not conexao.execute("SELECT 1 FROM convenios WHERE id=?", (convenio_id,)).fetchone():
            return {"sucesso": False, "erro": "Convênio não encontrado."}
        conexao.execute(
            "UPDATE convenios SET nome=?,valor_diaria=?,ativo=? WHERE id=?",
            (nome, valor_diaria, ativo, convenio_id),
        )
        conexao.commit()
        return {"sucesso": True, "id": convenio_id, "nome": nome,
                "valor_diaria": valor_diaria, "ativo": ativo}
    except sqlite3.IntegrityError:
        return {"sucesso": False, "erro": "Já existe um convênio com esse nome."}
    finally:
        conexao.close()

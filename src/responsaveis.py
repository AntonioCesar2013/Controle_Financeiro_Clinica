from src.banco import conectar


def cadastrar_responsavel(nome, cpf, telefone, email):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id, nome, cpf, telefone, email, ativo
        FROM responsaveis
        WHERE cpf = ?
        """,
        (cpf,)
    )

    responsavel = cursor.fetchone()

    if responsavel:
        conexao.close()
        return {
            "existe": True,
            "id": responsavel[0],
            "nome": responsavel[1],
            "cpf": responsavel[2],
            "telefone": responsavel[3],
            "email": responsavel[4],
            "ativo": responsavel[5]
        }

    cursor.execute(
        """
        INSERT INTO responsaveis (nome, cpf, telefone, email)
        VALUES (?, ?, ?, ?)
        """,
        (nome, cpf, telefone, email)
    )

    conexao.commit()

    id_responsavel = cursor.lastrowid

    conexao.close()

    return {
        "existe": False,
        "id": id_responsavel,
        "nome": nome,
        "cpf": cpf,
        "telefone": telefone,
        "email": email,
        "ativo": 1
    }


def buscar_responsavel_por_cpf(cpf):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id, nome, cpf, telefone, email, ativo
        FROM responsaveis
        WHERE cpf = ?
        """,
        (cpf,)
    )

    responsavel = cursor.fetchone()

    conexao.close()

    if responsavel is None:
        return None

    return {
        "id": responsavel[0],
        "nome": responsavel[1],
        "cpf": responsavel[2],
        "telefone": responsavel[3],
        "email": responsavel[4],
        "ativo": responsavel[5]
    }


def editar_responsavel(id_responsavel, nome, cpf, telefone, email, ativo):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        UPDATE responsaveis
        SET nome = ?,
            cpf = ?,
            telefone = ?,
            email = ?,
            ativo = ?
        WHERE id = ?
        """,
        (nome, cpf, telefone, email, ativo, id_responsavel)
    )

    conexao.commit()

    alterado = cursor.rowcount

    conexao.close()

    return alterado > 0
from src.banco import conectar


def cadastrar_residente(nome, cpf, cidade_origem):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id, nome, cpf, cidade_origem, ativo
        FROM residentes
        WHERE cpf = ?
        """,
        (cpf,)
    )

    residente = cursor.fetchone()

    if residente:
        conexao.close()
        return {
            "existe": True,
            "id": residente[0],
            "nome": residente[1],
            "cpf": residente[2],
            "cidade_origem": residente[3],
            "ativo": residente[4]
        }

    cursor.execute(
        """
        INSERT INTO residentes (nome, cpf, cidade_origem)
        VALUES (?, ?, ?)
        """,
        (nome, cpf, cidade_origem)
    )

    conexao.commit()

    id_residente = cursor.lastrowid

    conexao.close()

    return {
        "existe": False,
        "id": id_residente,
        "nome": nome,
        "cpf": cpf,
        "cidade_origem": cidade_origem,
        "ativo": 1
    }

def buscar_residente_por_cpf(cpf):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id, nome, cpf, cidade_origem, ativo
        FROM residentes
        WHERE cpf = ?
        """,
        (cpf,)
    )

    residente = cursor.fetchone()

    conexao.close()

    if residente is None:
        return None

    return {
        "id": residente[0],
        "nome": residente[1],
        "cpf": residente[2],
        "cidade_origem": residente[3],
        "ativo": residente[4]
    }


def editar_residente(id_residente, nome, cpf, cidade_origem, ativo):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        UPDATE residentes
        SET nome = ?,
            cpf = ?,
            cidade_origem = ?,
            ativo = ?
        WHERE id = ?
        """,
        (nome, cpf, cidade_origem, ativo, id_residente)
    )

    conexao.commit()

    alterado = cursor.rowcount

    conexao.close()

    return alterado > 0
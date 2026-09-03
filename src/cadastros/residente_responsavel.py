from src.infraestrutura.banco import conectar


def vincular_responsavel(
    residente_id,
    responsavel_id,
    relacao=None,
    principal=0
):
    conexao = conectar()
    cursor = conexao.cursor()

    # Verifica se o vínculo já existe
    cursor.execute(
        """
        SELECT id
        FROM residente_responsavel
        WHERE residente_id = ?
          AND responsavel_id = ?
        """,
        (residente_id, responsavel_id)
    )

    vinculo_existente = cursor.fetchone()

    if vinculo_existente:
        conexao.close()

        return {
            "sucesso": False,
            "existe": True,
            "id": vinculo_existente[0]
        }

    # Se este responsável será o principal,
    # tira o status de principal dos outros vínculos
    if principal:
        cursor.execute(
            """
            UPDATE residente_responsavel
            SET principal = 0
            WHERE residente_id = ?
            """,
            (residente_id,)
        )

    cursor.execute(
        """
        INSERT INTO residente_responsavel (
            residente_id,
            responsavel_id,
            relacao,
            principal
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            residente_id,
            responsavel_id,
            relacao,
            principal
        )
    )

    conexao.commit()

    id_vinculo = cursor.lastrowid

    conexao.close()

    return {
        "sucesso": True,
        "existe": False,
        "id": id_vinculo
    }


def buscar_responsaveis_do_residente(residente_id):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            rr.id,
            rr.residente_id,
            rr.responsavel_id,
            r.nome,
            r.cpf,
            r.telefone,
            r.email,
            rr.relacao,
            rr.principal
        FROM residente_responsavel rr
        INNER JOIN responsaveis r
            ON r.id = rr.responsavel_id
        WHERE rr.residente_id = ?
        ORDER BY rr.principal DESC, r.nome
        """,
        (residente_id,)
    )

    resultados = cursor.fetchall()

    conexao.close()

    responsaveis = []

    for resultado in resultados:
        responsaveis.append({
            "id": resultado[0],
            "residente_id": resultado[1],
            "responsavel_id": resultado[2],
            "nome": resultado[3],
            "cpf": resultado[4],
            "telefone": resultado[5],
            "email": resultado[6],
            "relacao": resultado[7],
            "principal": resultado[8]
        })

    return responsaveis


def remover_vinculo(id_vinculo):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        DELETE FROM residente_responsavel
        WHERE id = ?
        """,
        (id_vinculo,)
    )

    conexao.commit()

    removido = cursor.rowcount

    conexao.close()

    return removido > 0

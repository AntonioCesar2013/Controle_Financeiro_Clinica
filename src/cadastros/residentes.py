from src.infraestrutura.banco import conectar


def cadastrar_residente(nome, cpf, cidade_origem):
    nome = str(nome or "").strip()
    cpf_original = str(cpf or "").strip()
    cpf = cpf_original if cpf_original.startswith("PENDENTE-") else "".join(x for x in cpf_original if x.isdigit())
    cidade_origem = str(cidade_origem or "").strip() or None
    if not nome:
        return {"sucesso": False, "erro": "O nome do residente é obrigatório."}
    if not cpf.startswith("PENDENTE-") and len(cpf) != 11:
        return {"sucesso": False, "erro": "O CPF do residente deve conter 11 números."}
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
            "sucesso": True,
            "existe": True,
            "id": residente[0],
            "nome": residente[1],
            "cpf": residente[2],
            "cidade_origem": residente[3],
            "ativo": residente[4]
        }

    cursor.execute(
        """
        INSERT INTO residentes (nome, cpf, cidade_origem, ativo)
        VALUES (?, ?, ?, 0)
        """,
        (nome, cpf, cidade_origem)
    )

    conexao.commit()

    id_residente = cursor.lastrowid

    conexao.close()

    return {
        "sucesso": True,
        "existe": False,
        "id": id_residente,
        "nome": nome,
        "cpf": cpf,
        "cidade_origem": cidade_origem,
        "ativo": 0
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


def editar_residente(id_residente, nome, cpf, cidade_origem, ativo=None):
    nome = str(nome or "").strip()
    cpf = "".join(x for x in str(cpf or "") if x.isdigit())
    cidade_origem = str(cidade_origem or "").strip() or None
    if not nome:
        return {"sucesso": False, "erro": "O nome do residente é obrigatório."}
    if len(cpf) != 11:
        return {"sucesso": False, "erro": "O CPF do residente deve conter 11 números."}
    conexao = conectar()
    try:
        cursor = conexao.execute(
            "UPDATE residentes SET nome=?,cpf=?,cidade_origem=? WHERE id=?",
            (nome, cpf, cidade_origem, id_residente),
        )
        if cursor.rowcount == 0:
            return {"sucesso": False, "erro": "Residente não encontrado."}
        conexao.commit()
        return {"sucesso": True, "id": id_residente, "nome": nome, "cpf": cpf}
    except Exception as erro:
        if "UNIQUE" in str(erro).upper():
            return {"sucesso": False, "erro": "Já existe um residente com esse CPF."}
        raise
    finally:
        conexao.close()

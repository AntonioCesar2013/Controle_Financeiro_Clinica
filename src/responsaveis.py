from src.banco import conectar


def cadastrar_responsavel(nome, cpf, telefone, email):
    nome = str(nome or "").strip()
    cpf_original = str(cpf or "").strip()
    cpf = cpf_original if cpf_original.startswith("PENDENTE-") else "".join(x for x in cpf_original if x.isdigit())
    telefone = str(telefone or "").strip() or None
    email = str(email or "").strip() or None
    if not nome:
        return {"sucesso": False, "erro": "O nome do responsável é obrigatório."}
    if not cpf.startswith("PENDENTE-") and len(cpf) != 11:
        return {"sucesso": False, "erro": "O CPF do responsável deve conter 11 números."}
    if email and "@" not in email:
        return {"sucesso": False, "erro": "O e-mail informado é inválido."}
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
            "sucesso": True,
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
        "sucesso": True,
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

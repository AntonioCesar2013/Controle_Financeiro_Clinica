from src.banco import conectar


def cadastrar_responsavel(nome, cpf, telefone, email):
    nome = str(nome or "").strip()
    cpf_original = str(cpf or "").strip()
    cpf = cpf_original if cpf_original.startswith("PENDENTE-") else "".join(x for x in cpf_original if x.isdigit())
    telefone = str(telefone or "").strip() or None
    email = str(email or "").strip() or None
    if not nome:
        return {"sucesso": False, "erro": "O nome do responsável é obrigatório."}
    if not cpf.startswith("PENDENTE-") and len(cpf) not in (11, 14):
        return {"sucesso": False, "erro": "O CPF ou CNPJ do responsável deve conter 11 ou 14 números."}
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


def editar_responsavel(id_responsavel, nome, cpf, telefone, email, ativo=1):
    nome = str(nome or "").strip()
    cpf = "".join(x for x in str(cpf or "") if x.isdigit())
    telefone = str(telefone or "").strip() or None
    email = str(email or "").strip() or None
    try:
        ativo = int(ativo)
    except (TypeError, ValueError):
        ativo = -1
    if not nome:
        return {"sucesso": False, "erro": "O nome do responsável é obrigatório."}
    if len(cpf) not in (11, 14):
        return {"sucesso": False, "erro": "O CPF ou CNPJ do responsável deve conter 11 ou 14 números."}
    if email and "@" not in email:
        return {"sucesso": False, "erro": "O e-mail informado é inválido."}
    if ativo not in (0, 1):
        return {"sucesso": False, "erro": "Situação inválida."}
    conexao = conectar()
    try:
        cursor = conexao.execute(
            "UPDATE responsaveis SET nome=?,cpf=?,telefone=?,email=?,ativo=? WHERE id=?",
            (nome, cpf, telefone, email, ativo, id_responsavel),
        )
        if cursor.rowcount == 0:
            return {"sucesso": False, "erro": "Responsável não encontrado."}
        conexao.commit()
        return {"sucesso": True, "id": id_responsavel, "nome": nome, "cpf": cpf, "ativo": ativo}
    except Exception as erro:
        if "UNIQUE" in str(erro).upper():
            return {"sucesso": False, "erro": "Já existe um responsável com esse CPF ou CNPJ."}
        raise
    finally:
        conexao.close()

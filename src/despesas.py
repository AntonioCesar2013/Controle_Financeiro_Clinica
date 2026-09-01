from src.banco import conectar


# ============================================================
# CONSTANTES
# ============================================================

NATUREZAS_VALIDAS = {
    "FIXA",
    "VARIAVEL",
    "EXTRAORDINARIA",
}


# ============================================================
# SETORES
# ============================================================

def cadastrar_setor(nome):
    """
    Cadastra um novo setor.

    Retorna:
        {
            "sucesso": True,
            "id": ...,
            "nome": ...,
            "ativo": 1
        }

    Em caso de erro:
        {
            "sucesso": False,
            "erro": "..."
        }
    """

    nome = str(nome or "").strip()

    if not nome:
        return {
            "sucesso": False,
            "erro": "O nome do setor é obrigatório."
        }

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT id, nome, ativo
            FROM setores
            WHERE LOWER(nome) = LOWER(?)
        """, (nome,))

        existente = cursor.fetchone()

        if existente:
            return {
                "sucesso": False,
                "erro": "Já existe um setor com esse nome.",
                "id": existente[0]
            }

        cursor.execute("""
            INSERT INTO setores (nome)
            VALUES (?)
        """, (nome,))

        conexao.commit()

        return {
            "sucesso": True,
            "id": cursor.lastrowid,
            "nome": nome,
            "ativo": 1
        }

    finally:
        conexao.close()


def buscar_setor(setor_id):
    """
    Busca um setor pelo ID.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                nome,
                ativo
            FROM setores
            WHERE id = ?
        """, (setor_id,))

        resultado = cursor.fetchone()

        if not resultado:
            return {
                "sucesso": False,
                "erro": "Setor não encontrado."
            }

        return {
            "sucesso": True,
            "id": resultado[0],
            "nome": resultado[1],
            "ativo": resultado[2]
        }

    finally:
        conexao.close()


def listar_setores(apenas_ativos=True):
    """
    Lista os setores cadastrados.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        if apenas_ativos:
            cursor.execute("""
                SELECT id, nome, ativo
                FROM setores
                WHERE ativo = 1
                ORDER BY nome
            """)
        else:
            cursor.execute("""
                SELECT id, nome, ativo
                FROM setores
                ORDER BY nome
            """)

        resultados = cursor.fetchall()

        return [
            {
                "id": linha[0],
                "nome": linha[1],
                "ativo": linha[2]
            }
            for linha in resultados
        ]

    finally:
        conexao.close()


def desativar_setor(setor_id):
    """
    Desativa um setor sem apagar seu histórico.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT id
            FROM setores
            WHERE id = ?
        """, (setor_id,))

        if not cursor.fetchone():
            return {
                "sucesso": False,
                "erro": "Setor não encontrado."
            }

        cursor.execute("""
            UPDATE setores
            SET ativo = 0
            WHERE id = ?
        """, (setor_id,))

        conexao.commit()

        return {
            "sucesso": True,
            "id": setor_id
        }

    finally:
        conexao.close()


def editar_setor(setor_id, nome, ativo=1):
    nome = str(nome or "").strip()
    if not nome:
        return {"sucesso": False, "erro": "O nome do setor é obrigatório."}

    conexao = conectar()
    try:
        existente = conexao.execute("SELECT id FROM setores WHERE id = ?", (setor_id,)).fetchone()
        if not existente:
            return {"sucesso": False, "erro": "Setor não encontrado."}
        duplicado = conexao.execute(
            "SELECT id FROM setores WHERE LOWER(nome) = LOWER(?) AND id <> ?",
            (nome, setor_id),
        ).fetchone()
        if duplicado:
            return {"sucesso": False, "erro": "Já existe um setor com esse nome."}
        conexao.execute(
            "UPDATE setores SET nome = ?, ativo = ? WHERE id = ?",
            (nome, 1 if str(ativo) in ("1", "true", "True") else 0, setor_id),
        )
        conexao.commit()
        return {"sucesso": True, "id": setor_id, "nome": nome}
    finally:
        conexao.close()


# ============================================================
# TIPOS DE DESPESA
# ============================================================

def cadastrar_tipo_despesa(nome):
    """
    Cadastra um novo tipo de despesa.
    """

    nome = str(nome or "").strip()

    if not nome:
        return {
            "sucesso": False,
            "erro": "O nome do tipo de despesa é obrigatório."
        }

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT id, nome, ativo
            FROM tipos_despesa
            WHERE LOWER(nome) = LOWER(?)
        """, (nome,))

        existente = cursor.fetchone()

        if existente:
            return {
                "sucesso": False,
                "erro": "Já existe um tipo de despesa com esse nome.",
                "id": existente[0]
            }

        cursor.execute("""
            INSERT INTO tipos_despesa (nome)
            VALUES (?)
        """, (nome,))

        conexao.commit()

        return {
            "sucesso": True,
            "id": cursor.lastrowid,
            "nome": nome,
            "ativo": 1
        }

    finally:
        conexao.close()


def buscar_tipo_despesa(tipo_despesa_id):
    """
    Busca um tipo de despesa pelo ID.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                nome,
                ativo
            FROM tipos_despesa
            WHERE id = ?
        """, (tipo_despesa_id,))

        resultado = cursor.fetchone()

        if not resultado:
            return {
                "sucesso": False,
                "erro": "Tipo de despesa não encontrado."
            }

        return {
            "sucesso": True,
            "id": resultado[0],
            "nome": resultado[1],
            "ativo": resultado[2]
        }

    finally:
        conexao.close()


def listar_tipos_despesa(apenas_ativos=True):
    """
    Lista os tipos de despesa cadastrados.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        if apenas_ativos:
            cursor.execute("""
                SELECT id, nome, ativo
                FROM tipos_despesa
                WHERE ativo = 1
                ORDER BY nome
            """)
        else:
            cursor.execute("""
                SELECT id, nome, ativo
                FROM tipos_despesa
                ORDER BY nome
            """)

        resultados = cursor.fetchall()

        return [
            {
                "id": linha[0],
                "nome": linha[1],
                "ativo": linha[2]
            }
            for linha in resultados
        ]

    finally:
        conexao.close()


def desativar_tipo_despesa(tipo_despesa_id):
    """
    Desativa um tipo de despesa sem apagar o histórico.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT id
            FROM tipos_despesa
            WHERE id = ?
        """, (tipo_despesa_id,))

        if not cursor.fetchone():
            return {
                "sucesso": False,
                "erro": "Tipo de despesa não encontrado."
            }

        cursor.execute("""
            UPDATE tipos_despesa
            SET ativo = 0
            WHERE id = ?
        """, (tipo_despesa_id,))

        conexao.commit()

        return {
            "sucesso": True,
            "id": tipo_despesa_id
        }

    finally:
        conexao.close()


def editar_tipo_despesa(tipo_despesa_id, nome, ativo=1):
    nome = str(nome or "").strip()
    if not nome:
        return {"sucesso": False, "erro": "O nome do tipo de despesa é obrigatório."}

    conexao = conectar()
    try:
        existente = conexao.execute(
            "SELECT id FROM tipos_despesa WHERE id = ?", (tipo_despesa_id,)
        ).fetchone()
        if not existente:
            return {"sucesso": False, "erro": "Tipo de despesa não encontrado."}
        duplicado = conexao.execute(
            "SELECT id FROM tipos_despesa WHERE LOWER(nome) = LOWER(?) AND id <> ?",
            (nome, tipo_despesa_id),
        ).fetchone()
        if duplicado:
            return {"sucesso": False, "erro": "Já existe um tipo de despesa com esse nome."}
        conexao.execute(
            "UPDATE tipos_despesa SET nome = ?, ativo = ? WHERE id = ?",
            (nome, 1 if str(ativo) in ("1", "true", "True") else 0, tipo_despesa_id),
        )
        conexao.commit()
        return {"sucesso": True, "id": tipo_despesa_id, "nome": nome}
    finally:
        conexao.close()


# ============================================================
# DESPESAS
# ============================================================

def cadastrar_despesa(
    setor_id,
    tipo_despesa_id,
    descricao,
    natureza,
    recorrente=False
):
    """
    Cadastra uma nova despesa.

    natureza:
        FIXA
        VARIAVEL
        EXTRAORDINARIA

    recorrente:
        True / False
    """

    descricao = str(descricao or "").strip()
    natureza = str(natureza or "").strip().upper()

    if not descricao:
        return {
            "sucesso": False,
            "erro": "A descrição da despesa é obrigatória."
        }

    if natureza not in NATUREZAS_VALIDAS:
        return {
            "sucesso": False,
            "erro": (
                "Natureza inválida. "
                "Use FIXA, VARIAVEL ou EXTRAORDINARIA."
            )
        }

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        # --------------------------------------------------------
        # Verifica setor
        # --------------------------------------------------------

        cursor.execute("""
            SELECT id, nome, ativo
            FROM setores
            WHERE id = ?
        """, (setor_id,))

        setor = cursor.fetchone()

        if not setor:
            return {
                "sucesso": False,
                "erro": "Setor não encontrado."
            }

        if setor[2] != 1:
            return {
                "sucesso": False,
                "erro": "O setor está inativo."
            }

        # --------------------------------------------------------
        # Verifica tipo de despesa
        # --------------------------------------------------------

        cursor.execute("""
            SELECT id, nome, ativo
            FROM tipos_despesa
            WHERE id = ?
        """, (tipo_despesa_id,))

        tipo = cursor.fetchone()

        if not tipo:
            return {
                "sucesso": False,
                "erro": "Tipo de despesa não encontrado."
            }

        if tipo[2] != 1:
            return {
                "sucesso": False,
                "erro": "O tipo de despesa está inativo."
            }

        # --------------------------------------------------------
        # Cadastro
        # --------------------------------------------------------

        cursor.execute("""
            INSERT INTO despesas (
                setor_id,
                tipo_despesa_id,
                descricao,
                natureza,
                recorrente
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            setor_id,
            tipo_despesa_id,
            descricao,
            natureza,
            1 if recorrente else 0
        ))

        conexao.commit()

        return {
            "sucesso": True,
            "id": cursor.lastrowid,
            "setor_id": setor_id,
            "tipo_despesa_id": tipo_despesa_id,
            "descricao": descricao,
            "natureza": natureza,
            "recorrente": 1 if recorrente else 0,
            "ativo": 1
        }

    finally:
        conexao.close()


def buscar_despesa(despesa_id):
    """
    Busca uma despesa pelo ID.

    Retorna também os nomes do setor e do tipo de despesa.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT
                d.id,
                d.setor_id,
                s.nome,
                d.tipo_despesa_id,
                t.nome,
                d.descricao,
                d.natureza,
                d.recorrente,
                d.ativo
            FROM despesas d

            INNER JOIN setores s
                ON s.id = d.setor_id

            INNER JOIN tipos_despesa t
                ON t.id = d.tipo_despesa_id

            WHERE d.id = ?
        """, (despesa_id,))

        resultado = cursor.fetchone()

        if not resultado:
            return {
                "sucesso": False,
                "erro": "Despesa não encontrada."
            }

        return {
            "sucesso": True,
            "id": resultado[0],
            "setor_id": resultado[1],
            "setor_nome": resultado[2],
            "tipo_despesa_id": resultado[3],
            "tipo_despesa_nome": resultado[4],
            "descricao": resultado[5],
            "natureza": resultado[6],
            "recorrente": resultado[7],
            "ativo": resultado[8]
        }

    finally:
        conexao.close()


def listar_despesas(apenas_ativas=True):
    """
    Lista as despesas cadastradas.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        filtro = "WHERE d.ativo = 1" if apenas_ativas else ""

        cursor.execute(f"""
            SELECT
                d.id,
                d.setor_id,
                s.nome,
                d.tipo_despesa_id,
                t.nome,
                d.descricao,
                d.natureza,
                d.recorrente,
                d.ativo
            FROM despesas d

            INNER JOIN setores s
                ON s.id = d.setor_id

            INNER JOIN tipos_despesa t
                ON t.id = d.tipo_despesa_id

            {filtro}

            ORDER BY
                s.nome,
                t.nome,
                d.descricao
        """)

        resultados = cursor.fetchall()

        return [
            {
                "id": linha[0],
                "setor_id": linha[1],
                "setor_nome": linha[2],
                "tipo_despesa_id": linha[3],
                "tipo_despesa_nome": linha[4],
                "descricao": linha[5],
                "natureza": linha[6],
                "recorrente": linha[7],
                "ativo": linha[8]
            }
            for linha in resultados
        ]

    finally:
        conexao.close()


def desativar_despesa(despesa_id):
    """
    Desativa uma despesa sem apagar seu histórico.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT id
            FROM despesas
            WHERE id = ?
        """, (despesa_id,))

        if not cursor.fetchone():
            return {
                "sucesso": False,
                "erro": "Despesa não encontrada."
            }

        cursor.execute("""
            UPDATE despesas
            SET ativo = 0
            WHERE id = ?
        """, (despesa_id,))

        conexao.commit()

        return {
            "sucesso": True,
            "id": despesa_id
        }

    finally:
        conexao.close()


# ============================================================
# TESTE MANUAL
# ============================================================

if __name__ == "__main__":
    print("Módulo de despesas carregado com sucesso.")

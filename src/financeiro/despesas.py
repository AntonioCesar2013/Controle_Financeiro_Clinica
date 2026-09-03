"""Cadastros de setores e despesas, classificados somente pela natureza."""

from src.infraestrutura.banco import conectar


NATUREZAS_VALIDAS = {"FIXA", "VARIAVEL", "EXTRAORDINARIA"}


def cadastrar_setor(nome):
    nome = str(nome or "").strip()
    if not nome:
        return {"sucesso": False, "erro": "O nome do setor é obrigatório."}
    conexao = conectar()
    try:
        existente = conexao.execute(
            "SELECT id FROM setores WHERE LOWER(nome)=LOWER(?)", (nome,)
        ).fetchone()
        if existente:
            return {"sucesso": False, "erro": "Já existe um setor com esse nome.", "id": existente[0]}
        cursor = conexao.execute("INSERT INTO setores(nome) VALUES(?)", (nome,))
        conexao.commit()
        return {"sucesso": True, "id": cursor.lastrowid, "nome": nome, "ativo": 1}
    finally:
        conexao.close()


def buscar_setor(setor_id):
    conexao = conectar()
    try:
        resultado = conexao.execute(
            "SELECT id,nome,ativo FROM setores WHERE id=?", (setor_id,)
        ).fetchone()
        if not resultado:
            return {"sucesso": False, "erro": "Setor não encontrado."}
        return {"sucesso": True, "id": resultado[0], "nome": resultado[1], "ativo": resultado[2]}
    finally:
        conexao.close()


def listar_setores(apenas_ativos=True):
    conexao = conectar()
    try:
        filtro = " WHERE ativo=1" if apenas_ativos else ""
        return [
            {"id": linha[0], "nome": linha[1], "ativo": linha[2]}
            for linha in conexao.execute(f"SELECT id,nome,ativo FROM setores{filtro} ORDER BY nome")
        ]
    finally:
        conexao.close()


def desativar_setor(setor_id):
    conexao = conectar()
    try:
        if not conexao.execute("SELECT id FROM setores WHERE id=?", (setor_id,)).fetchone():
            return {"sucesso": False, "erro": "Setor não encontrado."}
        conexao.execute("UPDATE setores SET ativo=0 WHERE id=?", (setor_id,))
        conexao.commit()
        return {"sucesso": True, "id": setor_id}
    finally:
        conexao.close()


def editar_setor(setor_id, nome, ativo=1):
    nome = str(nome or "").strip()
    if not nome:
        return {"sucesso": False, "erro": "O nome do setor é obrigatório."}
    conexao = conectar()
    try:
        if not conexao.execute("SELECT id FROM setores WHERE id=?", (setor_id,)).fetchone():
            return {"sucesso": False, "erro": "Setor não encontrado."}
        if conexao.execute(
            "SELECT id FROM setores WHERE LOWER(nome)=LOWER(?) AND id<>?", (nome, setor_id)
        ).fetchone():
            return {"sucesso": False, "erro": "Já existe um setor com esse nome."}
        conexao.execute(
            "UPDATE setores SET nome=?,ativo=? WHERE id=?",
            (nome, 1 if str(ativo) in ("1", "true", "True") else 0, setor_id),
        )
        conexao.commit()
        return {"sucesso": True, "id": setor_id, "nome": nome}
    finally:
        conexao.close()


def cadastrar_despesa(setor_id, descricao, natureza, recorrente=False):
    descricao = str(descricao or "").strip()
    natureza = str(natureza or "").strip().upper()
    if not descricao:
        return {"sucesso": False, "erro": "A descrição da despesa é obrigatória."}
    if natureza not in NATUREZAS_VALIDAS:
        return {"sucesso": False, "erro": "Natureza inválida. Use FIXA, VARIAVEL ou EXTRAORDINARIA."}
    conexao = conectar()
    try:
        setor = conexao.execute("SELECT id,ativo FROM setores WHERE id=?", (setor_id,)).fetchone()
        if not setor:
            return {"sucesso": False, "erro": "Setor não encontrado."}
        if not setor[1]:
            return {"sucesso": False, "erro": "O setor está inativo."}
        cursor = conexao.execute(
            "INSERT INTO despesas(setor_id,descricao,natureza,recorrente) VALUES(?,?,?,?)",
            (setor_id, descricao, natureza, 1 if recorrente else 0),
        )
        conexao.commit()
        return {
            "sucesso": True, "id": cursor.lastrowid, "setor_id": setor_id,
            "descricao": descricao, "natureza": natureza,
            "recorrente": 1 if recorrente else 0, "ativo": 1,
        }
    finally:
        conexao.close()


def buscar_despesa(despesa_id):
    conexao = conectar()
    try:
        resultado = conexao.execute(
            """SELECT d.id,d.setor_id,s.nome,d.descricao,d.natureza,d.recorrente,d.ativo
               FROM despesas d JOIN setores s ON s.id=d.setor_id WHERE d.id=?""",
            (despesa_id,),
        ).fetchone()
        if not resultado:
            return {"sucesso": False, "erro": "Despesa não encontrada."}
        return {
            "sucesso": True, "id": resultado[0], "setor_id": resultado[1],
            "setor_nome": resultado[2], "descricao": resultado[3],
            "natureza": resultado[4], "recorrente": resultado[5], "ativo": resultado[6],
        }
    finally:
        conexao.close()


def listar_despesas(apenas_ativas=True):
    conexao = conectar()
    try:
        filtro = "WHERE d.ativo=1" if apenas_ativas else ""
        resultados = conexao.execute(
            f"""SELECT d.id,d.setor_id,s.nome,d.descricao,d.natureza,d.recorrente,d.ativo
                FROM despesas d JOIN setores s ON s.id=d.setor_id
                {filtro} ORDER BY s.nome,d.natureza,d.descricao"""
        ).fetchall()
        return [
            {"id": x[0], "setor_id": x[1], "setor_nome": x[2], "descricao": x[3],
             "natureza": x[4], "recorrente": x[5], "ativo": x[6]}
            for x in resultados
        ]
    finally:
        conexao.close()


def desativar_despesa(despesa_id):
    conexao = conectar()
    try:
        if not conexao.execute("SELECT id FROM despesas WHERE id=?", (despesa_id,)).fetchone():
            return {"sucesso": False, "erro": "Despesa não encontrada."}
        conexao.execute("UPDATE despesas SET ativo=0 WHERE id=?", (despesa_id,))
        conexao.commit()
        return {"sucesso": True, "id": despesa_id}
    finally:
        conexao.close()


if __name__ == "__main__":
    print("Módulo de despesas carregado com sucesso.")

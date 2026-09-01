import hashlib
import hmac
import secrets
import sqlite3

from src.banco import conectar


ITERACOES_HASH = 600_000


def _normalizar_cpf(cpf):
    return "".join(caractere for caractere in str(cpf or "") if caractere.isdigit())


def gerar_hash_senha(senha):
    if not isinstance(senha, str) or len(senha) < 8:
        raise ValueError("A senha deve possuir pelo menos 8 caracteres.")

    salt = secrets.token_bytes(16)
    hash_senha = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt,
        ITERACOES_HASH,
    )
    return f"pbkdf2_sha256${ITERACOES_HASH}${salt.hex()}${hash_senha.hex()}"


def verificar_senha(senha, valor_armazenado):
    try:
        algoritmo, iteracoes, salt, hash_esperado = valor_armazenado.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        hash_informado = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            bytes.fromhex(salt),
            int(iteracoes),
        ).hex()
        return hmac.compare_digest(hash_informado, hash_esperado)
    except (AttributeError, TypeError, ValueError):
        return False


def possui_colaboradores():
    conexao = conectar()
    try:
        return conexao.execute("SELECT EXISTS(SELECT 1 FROM colaboradores)").fetchone()[0] == 1
    finally:
        conexao.close()


def cadastrar_colaborador(nome, cpf, senha, status="ATIVO"):
    nome = str(nome or "").strip()
    cpf = _normalizar_cpf(cpf)
    status = str(status or "").strip().upper()

    if not nome:
        return {"sucesso": False, "erro": "O nome é obrigatório."}
    if len(cpf) != 11:
        return {"sucesso": False, "erro": "O CPF deve conter 11 dígitos."}
    if status not in ("ATIVO", "INATIVO"):
        return {"sucesso": False, "erro": "Status inválido."}

    try:
        senha_hash = gerar_hash_senha(senha)
    except ValueError as erro:
        return {"sucesso": False, "erro": str(erro)}

    conexao = conectar()
    try:
        cursor = conexao.execute(
            """
            INSERT INTO colaboradores (nome, cpf, senha_hash, status)
            VALUES (?, ?, ?, ?)
            """,
            (nome, cpf, senha_hash, status),
        )
        conexao.commit()
        return {"sucesso": True, "id": cursor.lastrowid, "nome": nome, "cpf": cpf, "status": status}
    except sqlite3.IntegrityError:
        return {"sucesso": False, "erro": "Já existe um colaborador com esse CPF."}
    finally:
        conexao.close()


def autenticar_colaborador(cpf, senha):
    cpf = _normalizar_cpf(cpf)
    conexao = conectar()
    conexao.row_factory = sqlite3.Row
    try:
        colaborador = conexao.execute(
            """
            SELECT id, nome, cpf, senha_hash, status
            FROM colaboradores
            WHERE cpf = ?
            """,
            (cpf,),
        ).fetchone()
    finally:
        conexao.close()

    if colaborador is None or colaborador["status"] != "ATIVO":
        return None
    if not verificar_senha(senha, colaborador["senha_hash"]):
        return None
    return {chave: colaborador[chave] for chave in ("id", "nome", "cpf", "status")}


def editar_colaborador(colaborador_id, nome, cpf, status):
    nome = str(nome or "").strip()
    cpf = _normalizar_cpf(cpf)
    status = str(status or "").strip().upper()
    if not nome:
        return {"sucesso": False, "erro": "O nome é obrigatório."}
    if len(cpf) != 11:
        return {"sucesso": False, "erro": "O CPF deve conter 11 dígitos."}
    if status not in ("ATIVO", "INATIVO"):
        return {"sucesso": False, "erro": "Status inválido."}
    conexao = conectar()
    try:
        atual = conexao.execute("SELECT status FROM colaboradores WHERE id=?", (colaborador_id,)).fetchone()
        if not atual:
            return {"sucesso": False, "erro": "Colaborador não encontrado."}
        if atual[0] == "ATIVO" and status == "INATIVO":
            ativos = conexao.execute("SELECT COUNT(*) FROM colaboradores WHERE status='ATIVO'").fetchone()[0]
            if ativos <= 1:
                return {"sucesso": False, "erro": "Mantenha pelo menos um colaborador ativo."}
        cursor = conexao.execute(
            """UPDATE colaboradores SET nome=?,cpf=?,status=?,atualizado_em=CURRENT_TIMESTAMP
               WHERE id=?""",
            (nome, cpf, status, colaborador_id),
        )
        conexao.commit()
        return {"sucesso": True, "id": colaborador_id, "nome": nome, "cpf": cpf, "status": status}
    except sqlite3.IntegrityError:
        return {"sucesso": False, "erro": "Já existe um colaborador com esse CPF."}
    finally:
        conexao.close()


def redefinir_senha(colaborador_id, nova_senha):
    try:
        senha_hash = gerar_hash_senha(nova_senha)
    except ValueError as erro:
        return {"sucesso": False, "erro": str(erro)}
    conexao = conectar()
    try:
        cursor = conexao.execute(
            "UPDATE colaboradores SET senha_hash=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (senha_hash, colaborador_id),
        )
        if cursor.rowcount == 0:
            return {"sucesso": False, "erro": "Colaborador não encontrado."}
        conexao.commit()
        return {"sucesso": True, "id": colaborador_id}
    finally:
        conexao.close()

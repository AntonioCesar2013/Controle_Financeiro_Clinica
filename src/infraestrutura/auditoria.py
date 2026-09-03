import json

from src.infraestrutura.banco import conectar


CAMPOS_SIGILOSOS = {"senha", "confirmacao_senha", "senha_hash"}


def registrar(acao, entidade, entidade_id=None, detalhes=None, colaborador=None, endereco_ip=None):
    detalhes_limpos = {
        chave: ("[PROTEGIDO]" if chave in CAMPOS_SIGILOSOS else valor)
        for chave, valor in (detalhes or {}).items()
    }
    conexao = conectar()
    try:
        conexao.execute(
            """INSERT INTO auditoria(
                   colaborador_id,colaborador_nome,acao,entidade,entidade_id,detalhes,endereco_ip
               ) VALUES(?,?,?,?,?,?,?)""",
            (
                colaborador.get("id") if colaborador else None,
                colaborador.get("nome") if colaborador else "Modo de testes (sem login)",
                str(acao), str(entidade), str(entidade_id) if entidade_id is not None else None,
                json.dumps(detalhes_limpos, ensure_ascii=False, default=str), endereco_ip,
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def listar(limite=500):
    conexao = conectar()
    conexao.row_factory = __import__("sqlite3").Row
    try:
        return [dict(linha) for linha in conexao.execute(
            """SELECT id,colaborador_id,colaborador_nome,acao,entidade,entidade_id,
                      detalhes,endereco_ip,criado_em
               FROM auditoria ORDER BY id DESC LIMIT ?""", (int(limite),)
        )]
    finally:
        conexao.close()

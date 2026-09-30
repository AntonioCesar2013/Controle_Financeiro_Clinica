import json

from src.infraestrutura.banco import conectar


CAMPOS_SIGILOSOS = {"senha", "confirmacao_senha", "senha_hash"}


def limpar(dados):
    if isinstance(dados, dict):
        return {chave: '[PROTEGIDO]' if chave.lower() in CAMPOS_SIGILOSOS else limpar(valor)
                for chave, valor in dados.items()}
    if isinstance(dados, list):
        return [limpar(valor) for valor in dados]
    return dados


def registrar(acao, entidade, entidade_id=None, detalhes=None, colaborador=None, endereco_ip=None):
    detalhes_limpos = limpar(detalhes or {})
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


def listar_paginado(pagina=1, tamanho=50):
    try:
        pagina, tamanho = int(pagina), int(tamanho)
    except (TypeError, ValueError) as erro:
        raise ValueError("Paginação inválida.") from erro
    if pagina < 1 or not 10 <= tamanho <= 100:
        raise ValueError("Paginação inválida.")
    conexao = conectar()
    conexao.row_factory = __import__("sqlite3").Row
    try:
        total = conexao.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]
        linhas = [dict(linha) for linha in conexao.execute(
            """SELECT id,colaborador_id,colaborador_nome,acao,entidade,entidade_id,
                      detalhes,endereco_ip,criado_em
               FROM auditoria ORDER BY id DESC LIMIT ? OFFSET ?""",
            (tamanho, (pagina - 1) * tamanho))]
        return {"linhas": linhas, "pagina": pagina, "tamanho": tamanho,
                "total_registros": total, "total_filtrado": total}
    finally:
        conexao.close()

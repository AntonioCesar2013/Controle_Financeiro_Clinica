import sqlite3

from src.banco import conectar


def _listar(sql, parametros=()):
    conexao = conectar()
    conexao.row_factory = sqlite3.Row
    try:
        return [dict(linha) for linha in conexao.execute(sql, parametros).fetchall()]
    finally:
        conexao.close()


def listar_residentes():
    from src.internacoes import sincronizar_status_residentes
    sincronizar_status_residentes()
    return _listar("SELECT id, nome, cpf, cidade_origem, ativo FROM residentes ORDER BY nome")


def listar_responsaveis():
    return _listar("SELECT id, nome, cpf, telefone, email, ativo FROM responsaveis ORDER BY nome")


def listar_internacoes():
    from src.internacoes import sincronizar_status_residentes
    sincronizar_status_residentes()
    return _listar(
        """
        SELECT i.id, r.nome AS residente_nome, rp.nome AS responsavel_nome,
               i.data_acolhimento, i.periodo_tratamento, i.valor_contrato,
               i.valor_acolhimento, i.valor_mensalidade, i.status
        FROM internacoes i
        INNER JOIN residentes r ON r.id = i.residente_id
        INNER JOIN responsaveis rp ON rp.id = i.responsavel_id
        ORDER BY i.data_acolhimento DESC, r.nome
        """
    )


def listar_colaboradores():
    return _listar(
        """
        SELECT id, nome, cpf, status, criado_em, atualizado_em
        FROM colaboradores
        ORDER BY nome
        """
    )


def listar_carteiras():
    return _listar(
        """
        SELECT c.id, c.residente_id, r.nome AS residente_nome, c.saldo, c.ativo,
               COUNT(m.id) AS quantidade_movimentacoes,
               MAX(m.data_movimentacao) AS ultima_movimentacao
        FROM carteiras c
        INNER JOIN residentes r ON r.id = c.residente_id
        LEFT JOIN movimentacoes_carteira m ON m.carteira_id = c.id
        GROUP BY c.id
        ORDER BY r.nome
        """
    )

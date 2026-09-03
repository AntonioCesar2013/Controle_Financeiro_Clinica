from src.infraestrutura.banco import conectar


def obter_configuracao():
    """Retorna a configuração financeira ativa da clínica."""
    conexao = conectar()

    try:
        conexao.row_factory = __import__("sqlite3").Row
        cursor = conexao.cursor()

        configuracao = cursor.execute(
            """
            SELECT
                id,
                aplicar_juros,
                tipo_juros,
                valor_juros,
                aplicar_multa,
                tipo_multa,
                valor_multa,
                ativo
            FROM configuracoes_financeiras
            WHERE ativo = 1
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()

        if configuracao is None:
            return None

        return dict(configuracao)

    finally:
        conexao.close()

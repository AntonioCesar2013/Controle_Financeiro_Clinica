import sqlite3

CAMINHO_BANCO = "dados/clinica.db"


def cadastrar_internacao(
    residente_id,
    responsavel_id,
    data_acolhimento,
    periodo_tratamento,
    valor_contrato,
    valor_acolhimento,
    valor_mensalidade
):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    # Verifica se o residente existe
    cursor.execute(
        "SELECT id FROM residentes WHERE id = ?",
        (residente_id,)
    )

    if cursor.fetchone() is None:
        conexao.close()
        return {
            "sucesso": False,
            "erro": "Residente não encontrado."
        }

    # Verifica se o responsável existe
    cursor.execute(
        "SELECT id FROM responsaveis WHERE id = ?",
        (responsavel_id,)
    )

    if cursor.fetchone() is None:
        conexao.close()
        return {
            "sucesso": False,
            "erro": "Responsável não encontrado."
        }

    # Cria a internação
    cursor.execute(
        """
        INSERT INTO internacoes (
            residente_id,
            responsavel_id,
            data_acolhimento,
            periodo_tratamento,
            valor_contrato,
            valor_acolhimento,
            valor_mensalidade
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            residente_id,
            responsavel_id,
            data_acolhimento,
            periodo_tratamento,
            valor_contrato,
            valor_acolhimento,
            valor_mensalidade
        )
    )

    internacao_id = cursor.lastrowid

    conexao.commit()
    conexao.close()

    return {
        "sucesso": True,
        "id": internacao_id
    }


def buscar_internacao(internacao_id):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            i.id,
            i.residente_id,
            r.nome AS residente_nome,
            i.responsavel_id,
            rp.nome AS responsavel_nome,
            i.data_acolhimento,
            i.periodo_tratamento,
            i.valor_contrato,
            i.valor_acolhimento,
            i.valor_mensalidade,
            i.status
        FROM internacoes i
        INNER JOIN residentes r
            ON r.id = i.residente_id
        INNER JOIN responsaveis rp
            ON rp.id = i.responsavel_id
        WHERE i.id = ?
        """,
        (internacao_id,)
    )

    resultado = cursor.fetchone()

    conexao.close()

    if resultado is None:
        return None

    return dict(resultado)
import sqlite3
from datetime import date
from calendar import monthrange

from src.banco import CAMINHO_BANCO


def adicionar_meses(data, meses):

    novo_mes = data.month - 1 + meses
    novo_ano = data.year + novo_mes // 12
    novo_mes = novo_mes % 12 + 1

    ultimo_dia = monthrange(novo_ano, novo_mes)[1]
    novo_dia = min(data.day, ultimo_dia)

    return date(novo_ano, novo_mes, novo_dia)


def gerar_cobrancas(internacao_id):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    # Busca a internação
    cursor.execute(
        """
        SELECT
            id,
            data_acolhimento,
            periodo_tratamento,
            valor_acolhimento,
            valor_mensalidade
        FROM internacoes
        WHERE id = ?
        """,
        (internacao_id,)
    )

    internacao = cursor.fetchone()

    if internacao is None:
        conexao.close()
        return {
            "sucesso": False,
            "erro": "Internação não encontrada."
        }

    # Verifica se já existem cobranças
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM cobrancas
        WHERE internacao_id = ?
        """,
        (internacao_id,)
    )

    quantidade = cursor.fetchone()[0]

    if quantidade > 0:
        conexao.close()
        return {
            "sucesso": False,
            "erro": "As cobranças desta internação já foram geradas."
        }

    data_inicio = date.fromisoformat(
        internacao["data_acolhimento"]
    )

    periodo = internacao["periodo_tratamento"]

    # Cria a cobrança do acolhimento
    cursor.execute(
        """
        INSERT INTO cobrancas (
            internacao_id,
            numero_parcela,
            tipo,
            data_vencimento,
            valor
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            internacao_id,
            0,
            "ACOLHIMENTO",
            data_inicio.isoformat(),
            internacao["valor_acolhimento"]
        )
    )

    # Cria as mensalidades
    for numero in range(1, periodo + 1):

        data_vencimento = adicionar_meses(
            data_inicio,
            numero
        )

        cursor.execute(
            """
            INSERT INTO cobrancas (
                internacao_id,
                numero_parcela,
                tipo,
                data_vencimento,
                valor
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                internacao_id,
                numero,
                "MENSALIDADE",
                data_vencimento.isoformat(),
                internacao["valor_mensalidade"]
            )
        )

    conexao.commit()
    conexao.close()

    return {
        "sucesso": True,
        "quantidade": periodo + 1
    }


def buscar_cobrancas(internacao_id):
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            id,
            internacao_id,
            numero_parcela,
            tipo,
            data_vencimento,
            valor,
            status
        FROM cobrancas
        WHERE internacao_id = ?
        ORDER BY numero_parcela
        """,
        (internacao_id,)
    )

    cobrancas = cursor.fetchall()

    conexao.close()

    return [dict(cobranca) for cobranca in cobrancas]
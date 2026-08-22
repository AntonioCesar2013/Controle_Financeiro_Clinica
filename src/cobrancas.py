from datetime import date
from dateutil.relativedelta import relativedelta

from .banco import conectar


def gerar_cobrancas(internacao_id):
    conexao = conectar()
    cursor = conexao.cursor()

    internacao = cursor.execute("""
        SELECT
            data_acolhimento,
            periodo_tratamento,
            valor_acolhimento,
            valor_mensalidade
        FROM internacoes
        WHERE id = ?
    """, (internacao_id,)).fetchone()

    if not internacao:
        conexao.close()
        return {
            "sucesso": False,
            "erro": "Internação não encontrada."
        }

    data_acolhimento = date.fromisoformat(internacao[0])
    periodo_tratamento = internacao[1]
    valor_acolhimento = internacao[2]
    valor_mensalidade = internacao[3]

    quantidade_existente = cursor.execute("""
        SELECT COUNT(*)
        FROM cobrancas
        WHERE internacao_id = ?
    """, (internacao_id,)).fetchone()[0]

    if quantidade_existente > 0:
        conexao.close()
        return {
            "sucesso": False,
            "erro": "As cobranças desta internação já foram geradas."
        }

    # Cobrança do acolhimento
    cursor.execute("""
        INSERT INTO cobrancas (
            internacao_id,
            numero_parcela,
            tipo,
            data_vencimento,
            valor,
            desconto,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        internacao_id,
        0,
        "ACOLHIMENTO",
        data_acolhimento.isoformat(),
        valor_acolhimento,
        0,
        "ABERTA"
    ))

    # Mensalidades
    for numero in range(1, periodo_tratamento + 1):
        data_vencimento = (
            data_acolhimento + relativedelta(months=numero)
        )

        cursor.execute("""
            INSERT INTO cobrancas (
                internacao_id,
                numero_parcela,
                tipo,
                data_vencimento,
                valor,
                desconto,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            internacao_id,
            numero,
            "MENSALIDADE",
            data_vencimento.isoformat(),
            valor_mensalidade,
            0,
            "ABERTA"
        ))

    conexao.commit()
    conexao.close()

    return {
        "sucesso": True,
        "quantidade": periodo_tratamento + 1
    }


def listar_cobrancas(internacao_id):
    conexao = conectar()
    cursor = conexao.cursor()

    cobrancas = cursor.execute("""
        SELECT
            id,
            internacao_id,
            numero_parcela,
            tipo,
            data_vencimento,
            valor,
            desconto,
            status
        FROM cobrancas
        WHERE internacao_id = ?
        ORDER BY numero_parcela
    """, (internacao_id,)).fetchall()

    conexao.close()

    resultado = []

    for cobranca in cobrancas:
        resultado.append({
            "id": cobranca[0],
            "internacao_id": cobranca[1],
            "numero_parcela": cobranca[2],
            "tipo": cobranca[3],
            "data_vencimento": cobranca[4],
            "valor": cobranca[5],
            "desconto": cobranca[6],
            "status": cobranca[7]
        })

    return resultado


def buscar_cobranca(cobranca_id):
    conexao = conectar()
    cursor = conexao.cursor()

    cobranca = cursor.execute("""
        SELECT
            id,
            internacao_id,
            numero_parcela,
            tipo,
            data_vencimento,
            valor,
            desconto,
            status
        FROM cobrancas
        WHERE id = ?
    """, (cobranca_id,)).fetchone()

    conexao.close()

    if not cobranca:
        return None

    return {
        "id": cobranca[0],
        "internacao_id": cobranca[1],
        "numero_parcela": cobranca[2],
        "tipo": cobranca[3],
        "data_vencimento": cobranca[4],
        "valor": cobranca[5],
        "desconto": cobranca[6],
        "status": cobranca[7]
    }


def aplicar_desconto(cobranca_id, valor_desconto):
    conexao = conectar()
    cursor = conexao.cursor()

    cobranca = cursor.execute("""
        SELECT
            valor,
            desconto,
            status
        FROM cobrancas
        WHERE id = ?
    """, (cobranca_id,)).fetchone()

    if not cobranca:
        conexao.close()
        return {
            "sucesso": False,
            "erro": "Cobrança não encontrada."
        }

    valor = cobranca[0]
    desconto_atual = cobranca[1]
    status = cobranca[2]

    if status == "PAGA":
        conexao.close()
        return {
            "sucesso": False,
            "erro": "Não é possível aplicar desconto em uma cobrança já paga."
        }

    if status == "DESCONTADA":
        conexao.close()
        return {
            "sucesso": False,
            "erro": "A cobrança já está totalmente descontada."
        }

    if valor_desconto <= 0:
        conexao.close()
        return {
            "sucesso": False,
            "erro": "O valor do desconto deve ser maior que zero."
        }

    desconto_disponivel = valor - desconto_atual

    if valor_desconto > desconto_disponivel:
        conexao.close()
        return {
            "sucesso": False,
            "erro": (
                f"O desconto não pode ser maior que o valor restante "
                f"da cobrança. Disponível para desconto: R$ {desconto_disponivel}"
            )
        }

    novo_desconto = desconto_atual + valor_desconto
    valor_devido = valor - novo_desconto

    if valor_devido == 0:
        novo_status = "DESCONTADA"
    else:
        novo_status = "ABERTA"

    cursor.execute("""
        UPDATE cobrancas
        SET
            desconto = ?,
            status = ?
        WHERE id = ?
    """, (
        novo_desconto,
        novo_status,
        cobranca_id
    ))

    conexao.commit()
    conexao.close()

    return {
        "sucesso": True,
        "cobranca_id": cobranca_id,
        "valor": valor,
        "desconto": novo_desconto,
        "valor_devido": valor_devido,
        "status": novo_status
    }
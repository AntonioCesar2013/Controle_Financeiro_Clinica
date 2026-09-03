from calendar import monthrange
from datetime import date, timedelta

from src.infraestrutura.banco import conectar
from src.financeiro.contas_receber import (
    buscar_cobranca_consolidada,
    listar_cobrancas_consolidadas,
)
from src.financeiro.parcelas import calcular_data_vencimento


def _competencias_diarias(inicio, fim, valor_diaria):
    cursor_data = inicio
    numero = 1
    while cursor_data <= fim:
        ultimo_dia = date(cursor_data.year, cursor_data.month, monthrange(cursor_data.year, cursor_data.month)[1])
        final_competencia = min(ultimo_dia, fim)
        dias = (final_competencia - cursor_data).days + 1
        yield numero, final_competencia, dias * valor_diaria
        numero += 1
        cursor_data = final_competencia + timedelta(days=1)


def ajustar_convenio_ao_encerrar(internacao_id, data_encerramento, conexao=None,
                               autorizar_ajuste_desconto=False):
    """Ajusta as diárias ainda não recebidas para os dias realmente utilizados."""
    propria = conexao is None
    conexao = conexao or conectar()
    try:
        if propria:
            conexao.execute("BEGIN IMMEDIATE")
        internacao = conexao.execute(
            "SELECT data_acolhimento,modalidade,valor_diaria FROM internacoes WHERE id=?",
            (internacao_id,),
        ).fetchone()
        if not internacao or internacao[1] != "CONVENIO":
            return
        competencias = {numero: (fim.isoformat(), valor) for numero, fim, valor in _competencias_diarias(
            date.fromisoformat(internacao[0]), date.fromisoformat(data_encerramento), internacao[2]
        )}
        cobrancas = conexao.execute(
            """SELECT c.id,c.numero_parcela,c.valor,c.desconto,
                      COALESCE((SELECT SUM(r.valor) FROM recebimentos r WHERE r.cobranca_id=c.id),0)
               FROM cobrancas c WHERE c.internacao_id=?""", (internacao_id,)
        ).fetchall()
        for cobranca_id, numero, valor_anterior, desconto, recebido in cobrancas:
            vencimento, valor = competencias.get(numero, (data_encerramento, 0))
            if recebido > valor:
                raise ValueError(
                    f"Cobrança {cobranca_id}: recebido R$ {recebido / 100:.2f}, "
                    f"mas o valor após encerramento é R$ {valor / 100:.2f}. "
                    "Faça o acerto dos recebimentos antes de encerrar. Nenhuma alteração foi salva."
                )
            novo_desconto = min(desconto, valor - recebido)
            if novo_desconto != desconto and not autorizar_ajuste_desconto:
                raise ValueError(
                    f"Cobrança {cobranca_id}: o desconto deverá passar de R$ {desconto / 100:.2f} "
                    f"para R$ {novo_desconto / 100:.2f}. Marque a autorização de ajuste "
                    "dos descontos para concluir. Nenhuma alteração foi salva."
                )
            if valor != valor_anterior or novo_desconto != desconto:
                conexao.execute(
                    """INSERT INTO ajustes_cobrancas(cobranca_id,valor_anterior,valor_novo,
                       desconto_anterior,desconto_novo,motivo) VALUES(?,?,?,?,?,?)""",
                    (cobranca_id, valor_anterior, valor, desconto, novo_desconto,
                     f"Encerramento de convênio em {data_encerramento}"),
                )
            devido = valor - novo_desconto
            status = "DESCONTADA" if devido == 0 else "PAGA" if recebido == devido else "PARCIAL" if recebido else "ABERTA"
            conexao.execute(
                "UPDATE cobrancas SET data_vencimento=?,valor=?,desconto=?,status=? WHERE id=?",
                (vencimento, valor, novo_desconto, status, cobranca_id),
            )
        total = conexao.execute(
            "SELECT COALESCE(SUM(valor),0) FROM cobrancas WHERE internacao_id=?", (internacao_id,)
        ).fetchone()[0]
        conexao.execute("UPDATE internacoes SET valor_contrato=? WHERE id=?", (total, internacao_id))
        if propria:
            conexao.commit()
    except Exception:
        if propria:
            conexao.rollback()
        raise
    finally:
        if propria:
            conexao.close()


def gerar_cobrancas(internacao_id, conexao=None):
    conexao_propria = conexao is None
    conexao = conexao or conectar()
    cursor = conexao.cursor()

    internacao = cursor.execute("""
        SELECT
            data_acolhimento,
            periodo_tratamento,
            valor_acolhimento,
            valor_mensalidade
            ,modalidade,valor_diaria
        FROM internacoes
        WHERE id = ?
    """, (internacao_id,)).fetchone()

    if not internacao:
        if conexao_propria:
            conexao.close()
        return {
            "sucesso": False,
            "erro": "Internação não encontrada."
        }

    data_acolhimento = internacao[0]
    periodo_tratamento = internacao[1]
    valor_acolhimento = internacao[2]
    valor_mensalidade = internacao[3]
    modalidade = internacao[4]
    valor_diaria = internacao[5]

    quantidade_existente = cursor.execute("""
        SELECT COUNT(*)
        FROM cobrancas
        WHERE internacao_id = ?
    """, (internacao_id,)).fetchone()[0]

    if quantidade_existente > 0:
        if conexao_propria:
            conexao.close()
        return {
            "sucesso": False,
            "erro": "As cobranças desta internação já foram geradas."
        }

    if modalidade in ("SOCIAL", "VOLUNTARIO"):
        if conexao_propria:
            conexao.close()
        return {"sucesso": True, "quantidade": 0}

    if modalidade == "CONVENIO":
        inicio = date.fromisoformat(data_acolhimento)
        fim = calcular_data_vencimento(data_acolhimento, periodo_tratamento)
        total = 0
        quantidade = 0
        for numero, final_competencia, valor in _competencias_diarias(inicio, fim, valor_diaria):
            cursor.execute(
                """INSERT INTO cobrancas(internacao_id,numero_parcela,tipo,data_vencimento,valor,desconto,status)
                   VALUES(?,?,?,?,?,0,?)""",
                (internacao_id, numero, "MENSALIDADE", final_competencia.isoformat(), valor,
                 "ABERTA" if valor else "DESCONTADA"),
            )
            total += valor
            quantidade += 1
        cursor.execute("UPDATE internacoes SET valor_contrato=? WHERE id=?", (total, internacao_id))
        if conexao_propria:
            conexao.commit()
            conexao.close()
        return {"sucesso": True, "quantidade": quantidade}

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
        data_acolhimento,
        valor_acolhimento,
        0,
        "ABERTA" if valor_acolhimento else "DESCONTADA"
    ))

    # Mensalidades
    for numero in range(1, periodo_tratamento + 1):
        data_vencimento = calcular_data_vencimento(
            data_acolhimento,
            numero,
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
            "ABERTA" if valor_mensalidade else "DESCONTADA"
        ))

    if conexao_propria:
        conexao.commit()
        conexao.close()

    return {
        "sucesso": True,
        "quantidade": periodo_tratamento + 1
    }


def listar_cobrancas(internacao_id, data_referencia=None):
    """Lista cobranças da internação com informações consolidadas de recebimento."""
    return listar_cobrancas_consolidadas(
        internacao_id=internacao_id,
        data_referencia=data_referencia,
    )


def buscar_cobranca(cobranca_id, data_referencia=None):
    """Busca uma cobrança com informações consolidadas de recebimento."""
    return buscar_cobranca_consolidada(
        cobranca_id,
        data_referencia=data_referencia,
    )


def aplicar_desconto(cobranca_id, valor_desconto):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("BEGIN IMMEDIATE")

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

    total_recebido = cursor.execute(
        "SELECT COALESCE(SUM(valor), 0) FROM recebimentos WHERE cobranca_id = ?",
        (cobranca_id,),
    ).fetchone()[0]
    desconto_disponivel = valor - desconto_atual - total_recebido

    if valor_desconto > desconto_disponivel:
        conexao.close()
        return {
            "sucesso": False,
            "erro": (
                f"O desconto não pode ser maior que o valor restante "
                f"da cobrança. Disponível para desconto: R$ {desconto_disponivel / 100:.2f}"
            )
        }

    novo_desconto = desconto_atual + valor_desconto
    valor_devido = valor - novo_desconto

    if valor_devido == 0 and total_recebido == 0:
        novo_status = "DESCONTADA"
    elif total_recebido == valor_devido:
        novo_status = "PAGA"
    elif total_recebido > 0:
        novo_status = "PARCIAL"
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

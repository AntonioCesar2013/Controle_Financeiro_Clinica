import sqlite3
import unicodedata
from datetime import date

from src.infraestrutura.banco import conectar
from src.infraestrutura.transacoes import ATUAL, Transacao
from src.financeiro.despesas import validar_para_lancamento
from src.financeiro.moeda import validar_centavos


# ============================================================
# STATUS
# ============================================================

STATUS_ABERTA = "ABERTA"
STATUS_PARCIAL = "PARCIAL"
STATUS_PAGA = "PAGA"
STATUS_CANCELADA = "CANCELADA"


def registrar_compra_avista(despesa_id, data_pagamento, valor, forma_pagamento=None,
                            fornecedor=None, documento=None, observacao=None):
    """Cria a conta e seu pagamento integral em uma única transação."""
    from src.financeiro import pagamentos

    detalhes = []
    if str(fornecedor or "").strip():
        detalhes.append(f"Fornecedor: {str(fornecedor).strip()}")
    if str(documento or "").strip():
        detalhes.append(f"Documento: {str(documento).strip()}")
    if str(observacao or "").strip():
        detalhes.append(str(observacao).strip())
    texto = " | ".join(detalhes) or None

    def executar():
        conta = cadastrar_conta(despesa_id, data_pagamento, valor)
        if not conta.get("sucesso"):
            return conta
        pagamento = pagamentos.registrar_pagamento(
            conta["id"], data_pagamento, valor, forma_pagamento, texto,
        )
        if not pagamento.get("sucesso"):
            return pagamento
        return {
            "sucesso": True,
            "id": pagamento["id"],
            "conta_pagar_id": conta["id"],
            "data_pagamento": data_pagamento,
            "valor": pagamento["valor"],
            "forma_pagamento": pagamento["forma_pagamento"],
            "status": pagamento["status"],
        }

    if ATUAL.get() is not None:
        return executar()

    conexao = conectar()
    conexao.execute("BEGIN IMMEDIATE")
    token = ATUAL.set(Transacao(conexao))
    try:
        resultado = executar()
        if resultado.get("sucesso"):
            conexao.commit()
        else:
            conexao.rollback()
        return resultado
    except BaseException:
        conexao.rollback()
        raise
    finally:
        ATUAL.reset(token)
        conexao.close()


def corrigir_compra_avista(conta_id, motivo):
    """Estorna o pagamento e cancela a conta, preservando o pagamento no histórico."""
    from src.financeiro import pagamentos

    motivo = str(motivo or "").strip()
    if not motivo:
        return {"sucesso": False, "erro": "Informe o motivo da correção."}

    def executar():
        conexao = conectar()
        try:
            conta = conexao.execute(
                "SELECT valor,desconto,status FROM contas_pagar WHERE id=?", (conta_id,)
            ).fetchone()
            lancamentos = conexao.execute(
                "SELECT id,valor,desconto FROM pagamentos_saida WHERE conta_pagar_id=? ORDER BY id",
                (conta_id,),
            ).fetchall()
        finally:
            conexao.close()
        if not conta:
            return {"sucesso": False, "erro": "Conta a pagar não encontrada."}
        if conta[2] != STATUS_PAGA or len(lancamentos) != 1:
            return {"sucesso": False, "erro": "A correção completa é exclusiva para compras à vista com um único pagamento integral."}
        if lancamentos[0][1] + lancamentos[0][2] != conta[0]:
            return {"sucesso": False, "erro": "O pagamento não corresponde ao valor integral da compra."}
        estorno = pagamentos.excluir_pagamento(lancamentos[0][0], motivo)
        if not estorno.get("sucesso"):
            return estorno
        cancelamento = cancelar_conta(conta_id)
        if not cancelamento.get("sucesso"):
            return cancelamento
        return {"sucesso": True, "id": conta_id, "pagamento_id": lancamentos[0][0],
                "status": STATUS_CANCELADA}

    if ATUAL.get() is not None:
        return executar()
    conexao = conectar()
    conexao.execute("BEGIN IMMEDIATE")
    token = ATUAL.set(Transacao(conexao))
    try:
        resultado = executar()
        (conexao.commit if resultado.get("sucesso") else conexao.rollback)()
        return resultado
    except BaseException:
        conexao.rollback()
        raise
    finally:
        ATUAL.reset(token)
        conexao.close()


# ============================================================
# CADASTRAR CONTA A PAGAR
# ============================================================

def cadastrar_conta(despesa_id, data_vencimento, valor):
    """
    Cadastra uma nova conta a pagar vinculada a uma despesa.

    Parâmetros:
        despesa_id: ID da despesa
        data_vencimento: data no formato YYYY-MM-DD
        valor: valor da conta em centavos

    Retorna:
        {
            "sucesso": True,
            "id": ...,
            "despesa_id": ...,
            "data_vencimento": ...,
            "valor": ...,
            "status": "ABERTA"
        }
    """

    if not despesa_id:
        return {
            "sucesso": False,
            "erro": "O ID da despesa é obrigatório."
        }

    if not data_vencimento:
        return {
            "sucesso": False,
            "erro": "A data de vencimento é obrigatória."
        }

    try:
        if not isinstance(data_vencimento, str) or date.fromisoformat(data_vencimento).isoformat() != data_vencimento:
            raise ValueError
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Informe uma data de vencimento válida no formato YYYY-MM-DD."}

    try:
        valor = validar_centavos(valor)
    except ValueError as erro:
        return {"sucesso": False, "erro": str(erro)}
    if valor <= 0:
        return {
            "sucesso": False,
            "erro": "O valor da conta deve ser maior que zero."
        }

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute('BEGIN IMMEDIATE')
        try:
            validar_para_lancamento(conexao, despesa_id)
        except ValueError as erro:
            return {'sucesso': False, 'erro': str(erro)}
        # --------------------------------------------------------
        # Verifica se a despesa existe
        # --------------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                descricao,
                ativo
            FROM despesas
            WHERE id = ?
        """, (despesa_id,))

        despesa = cursor.fetchone()

        if not despesa:
            return {
                "sucesso": False,
                "erro": "Despesa não encontrada."
            }

        if despesa[2] != 1:
            return {
                "sucesso": False,
                "erro": "A despesa está inativa."
            }

        # --------------------------------------------------------
        # Cadastra a conta
        # --------------------------------------------------------

        cursor.execute("""
            INSERT INTO contas_pagar (
                despesa_id,
                data_vencimento,
                valor,
                status
            )
            VALUES (?, ?, ?, ?)
        """, (
            despesa_id,
            data_vencimento,
            valor,
            STATUS_ABERTA
        ))

        conexao.commit()

        return {
            "sucesso": True,
            "id": cursor.lastrowid,
            "despesa_id": despesa_id,
            "data_vencimento": data_vencimento,
            "valor": valor,
            "status": STATUS_ABERTA
        }

    finally:
        conexao.close()


# ============================================================
# BUSCAR CONTA
# ============================================================

def buscar_conta(conta_id):
    """
    Busca uma conta a pagar pelo ID.

    Também retorna os dados da despesa e do setor.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:

        cursor.execute("""
            SELECT
                c.id,
                c.despesa_id,
                d.descricao,
                d.natureza,
                d.recorrente,

                d.setor_id,
                s.nome,

                c.data_vencimento,
                c.valor,
                c.desconto,
                c.status

            FROM contas_pagar c

            INNER JOIN despesas d
                ON d.id = c.despesa_id

            INNER JOIN setores s
                ON s.id = d.setor_id

            WHERE c.id = ?
        """, (conta_id,))

        resultado = cursor.fetchone()

        if not resultado:
            return {
                "sucesso": False,
                "erro": "Conta a pagar não encontrada."
            }

        return {
            "sucesso": True,

            "id": resultado[0],

            "despesa_id": resultado[1],
            "despesa_descricao": resultado[2],
            "natureza": resultado[3],
            "recorrente": resultado[4],

            "setor_id": resultado[5],
            "setor_nome": resultado[6],

            "data_vencimento": resultado[7],
            "valor": resultado[8],
            "desconto": resultado[9],
            "status": resultado[10],
        }

    finally:
        conexao.close()


# ============================================================
# LISTAR CONTAS
# ============================================================

def listar_contas(
    status=None,
    data_inicio=None,
    data_fim=None
):
    """
    Lista contas a pagar.

    Pode filtrar por:

        status
        data_inicio
        data_fim
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:

        sql = """
            SELECT
                c.id,
                c.despesa_id,
                d.descricao,

                s.nome,

                d.natureza,
                d.recorrente,

                c.data_vencimento,
                c.valor,
                c.desconto,
                c.status,
                COALESCE((SELECT SUM(p.valor) FROM pagamentos_saida p WHERE p.conta_pagar_id=c.id), 0),
                COALESCE((SELECT SUM(p.multa_juros) FROM pagamentos_saida p WHERE p.conta_pagar_id=c.id), 0)

            FROM contas_pagar c

            INNER JOIN despesas d
                ON d.id = c.despesa_id

            INNER JOIN setores s
                ON s.id = d.setor_id

            WHERE 1 = 1
        """

        parametros = []

        # --------------------------------------------------------
        # Filtro por status
        # --------------------------------------------------------

        if status:
            sql += """
                AND c.status = ?
            """

            parametros.append(status)

        # --------------------------------------------------------
        # Filtro por data inicial
        # --------------------------------------------------------

        if data_inicio:
            sql += """
                AND c.data_vencimento >= ?
            """

            parametros.append(data_inicio)

        # --------------------------------------------------------
        # Filtro por data final
        # --------------------------------------------------------

        if data_fim:
            sql += """
                AND c.data_vencimento <= ?
            """

            parametros.append(data_fim)

        sql += """
            ORDER BY
                c.data_vencimento,
                s.nome,
                d.descricao
        """

        cursor.execute(sql, parametros)

        resultados = cursor.fetchall()

        return [
            {
                "id": linha[0],
                "despesa_id": linha[1],
                "despesa_descricao": linha[2],
                "setor_nome": linha[3],
                "natureza": linha[4],
                "recorrente": linha[5],
                "data_vencimento": linha[6],
                "valor": linha[7],
                "desconto": linha[8],
                "status": linha[9],
                "valor_devido": linha[7] - linha[8],
                "total_pago": linha[10],
                "total_multa_juros": linha[11],
                "total_pago_com_encargos": linha[10] + linha[11],
                "restante": linha[7] - linha[8] - linha[10],
            }
            for linha in resultados
        ]

    finally:
        conexao.close()


def listar_contas_paginadas(status=None, data_inicio=None, data_fim=None, busca=None,
                            pagina=1, tamanho=50, ordem="vencimento_asc", completo=False):
    """Lista contas com filtros aplicados no servidor e totais independentes da página."""
    try:
        pagina = max(1, int(pagina))
        tamanho = max(1, min(int(tamanho), 200))
    except (TypeError, ValueError) as erro:
        raise ValueError("Página ou tamanho de página inválido.") from erro
    ordens = {
        "vencimento_asc": "data_vencimento ASC, id ASC",
        "vencimento_desc": "data_vencimento DESC, id DESC",
        "descricao_asc": "despesa_descricao COLLATE NOCASE ASC, id ASC",
        "descricao_desc": "despesa_descricao COLLATE NOCASE DESC, id DESC",
    }
    if ordem not in ordens:
        raise ValueError("Ordenação de contas inválida.")

    def normalizar(valor):
        return "".join(c for c in unicodedata.normalize("NFD", str(valor or ""))
                       if unicodedata.category(c) != "Mn").casefold()

    conexao = conectar()
    conexao.row_factory = sqlite3.Row
    conexao.create_function("normalizar", 1, normalizar, deterministic=True)
    base = """WITH pagamentos AS (
            SELECT conta_pagar_id, SUM(valor) total_pago, SUM(multa_juros) total_multa_juros
            FROM pagamentos_saida GROUP BY conta_pagar_id
        ), contas AS (
            SELECT c.id,c.despesa_id,d.descricao despesa_descricao,s.nome setor_nome,
                   d.natureza,d.recorrente,c.data_vencimento,c.valor,c.desconto,c.status,
                   COALESCE(p.total_pago,0) total_pago,COALESCE(p.total_multa_juros,0) total_multa_juros,
                   c.valor-c.desconto-COALESCE(p.total_pago,0) restante
            FROM contas_pagar c JOIN despesas d ON d.id=c.despesa_id
            JOIN setores s ON s.id=d.setor_id LEFT JOIN pagamentos p ON p.conta_pagar_id=c.id
        )"""
    filtros, parametros = [], []
    if status:
        filtros.append("status=?")
        parametros.append(status)
    if data_inicio:
        filtros.append("data_vencimento>=?")
        parametros.append(data_inicio)
    if data_fim:
        filtros.append("data_vencimento<=?")
        parametros.append(data_fim)
    if busca and normalizar(busca):
        filtros.append("normalizar(despesa_descricao||' '||setor_nome||' '||natureza) LIKE ?")
        parametros.append(f"%{normalizar(busca)}%")
    where = " WHERE " + " AND ".join(filtros) if filtros else ""
    try:
        totais = "SELECT COUNT(*),COALESCE(SUM(valor),0),COALESCE(SUM(CASE WHEN status='CANCELADA' THEN 0 ELSE restante END),0) FROM contas"
        geral = conexao.execute(base + " " + totais).fetchone()
        filtrado = conexao.execute(base + " " + totais + where, parametros).fetchone()
        consulta = base + f" SELECT * FROM contas{where} ORDER BY {ordens[ordem]}"
        argumentos = tuple(parametros)
        if not completo:
            consulta += " LIMIT ? OFFSET ?"
            argumentos += (tamanho, (pagina - 1) * tamanho)
        linhas = conexao.execute(consulta, argumentos).fetchall()
        return {
            "linhas": [{**dict(linha), "valor_devido": linha["valor"] - linha["desconto"],
                        "total_pago_com_encargos": linha["total_pago"] + linha["total_multa_juros"]}
                       for linha in linhas],
            "pagina": pagina, "tamanho": tamanho,
            "total_registros": geral[0], "total_filtrado": filtrado[0],
            "totais_gerais": {"valor": geral[1], "restante": geral[2]},
            "totais_filtrados": {"valor": filtrado[1], "restante": filtrado[2]},
        }
    finally:
        conexao.close()


# ============================================================
# CALCULAR TOTAL RECEBIDO/PAGO
# ============================================================

def calcular_total_pago(conta_id):
    """
    Calcula quanto já foi pago de uma conta.

    Os pagamentos ficam na tabela pagamentos_saida.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:

        # --------------------------------------------------------
        # Verifica conta
        # --------------------------------------------------------

        cursor.execute("""
            SELECT id, valor, desconto, status
            FROM contas_pagar
            WHERE id = ?
        """, (conta_id,))

        conta = cursor.fetchone()

        if not conta:
            return {
                "sucesso": False,
                "erro": "Conta a pagar não encontrada."
            }

        # --------------------------------------------------------
        # Soma pagamentos
        # --------------------------------------------------------

        cursor.execute("""
            SELECT COALESCE(SUM(valor), 0), COALESCE(SUM(multa_juros), 0)
            FROM pagamentos_saida
            WHERE conta_pagar_id = ?
        """, (conta_id,))

        total_pago, total_multa_juros = cursor.fetchone()

        valor_conta = conta[1]
        desconto = conta[2]
        valor_devido = valor_conta - desconto

        restante = valor_devido - total_pago

        return {
            "sucesso": True,
            "conta_id": conta_id,
            "valor_conta": valor_conta,
            "valor_devido": valor_devido,
            "desconto": desconto,
            "total_pago": total_pago,
            "total_multa_juros": total_multa_juros,
            "total_pago_com_encargos": total_pago + total_multa_juros,
            "restante": restante,
            "status": conta[3]
        }

    finally:
        conexao.close()


# ============================================================
# ATUALIZAR STATUS
# ============================================================

def atualizar_status_conta(conta_id):
    """
    Atualiza automaticamente o status da conta
    com base nos pagamentos registrados.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:

        # --------------------------------------------------------
        # Busca conta
        # --------------------------------------------------------

        cursor.execute("""
            SELECT
                valor,
                desconto,
                status
            FROM contas_pagar
            WHERE id = ?
        """, (conta_id,))

        conta = cursor.fetchone()

        if not conta:
            return {
                "sucesso": False,
                "erro": "Conta a pagar não encontrada."
            }

        valor_conta = conta[0]
        desconto = conta[1]
        status_atual = conta[2]
        valor_devido = valor_conta - desconto

        # --------------------------------------------------------
        # Não altera conta cancelada
        # --------------------------------------------------------

        if status_atual == STATUS_CANCELADA:
            return {
                "sucesso": False,
                "erro": "A conta está cancelada."
            }

        # --------------------------------------------------------
        # Soma pagamentos
        # --------------------------------------------------------

        cursor.execute("""
            SELECT COALESCE(SUM(valor), 0)
            FROM pagamentos_saida
            WHERE conta_pagar_id = ?
        """, (conta_id,))

        total_pago = cursor.fetchone()[0]

        # --------------------------------------------------------
        # Define novo status
        # --------------------------------------------------------

        if total_pago == 0:
            novo_status = STATUS_ABERTA

        elif total_pago < valor_devido:
            novo_status = STATUS_PARCIAL

        elif total_pago == valor_devido:
            novo_status = STATUS_PAGA

        else:
            return {
                "sucesso": False,
                "erro": (
                    "Os pagamentos registrados ultrapassam "
                    "o valor da conta."
                )
            }

        # --------------------------------------------------------
        # Atualiza
        # --------------------------------------------------------

        cursor.execute("""
            UPDATE contas_pagar
            SET status = ?
            WHERE id = ?
        """, (
            novo_status,
            conta_id
        ))

        conexao.commit()

        return {
            "sucesso": True,
            "conta_id": conta_id,
            "valor_conta": valor_conta,
            "total_pago": total_pago,
            "valor_devido": valor_devido,
            "restante": valor_devido - total_pago,
            "status": novo_status
        }

    finally:
        conexao.close()


# ============================================================
# CANCELAR CONTA
# ============================================================

def cancelar_conta(conta_id):
    """
    Cancela uma conta a pagar.

    A conta não é apagada do banco.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                valor,
                status
            FROM contas_pagar
            WHERE id = ?
        """, (conta_id,))

        conta = cursor.fetchone()

        if not conta:
            return {
                "sucesso": False,
                "erro": "Conta a pagar não encontrada."
            }

        if conta[2] == STATUS_PAGA:
            return {
                "sucesso": False,
                "erro": "Não é possível cancelar uma conta já paga."
            }

        if conta[2] == STATUS_CANCELADA:
            return {
                "sucesso": False,
                "erro": "A conta já está cancelada."
            }

        # --------------------------------------------------------
        # Verifica se existem pagamentos
        # --------------------------------------------------------

        cursor.execute("""
            SELECT COALESCE(SUM(valor), 0)
            FROM pagamentos_saida
            WHERE conta_pagar_id = ?
        """, (conta_id,))

        total_pago = cursor.fetchone()[0]

        if total_pago > 0:
            return {
                "sucesso": False,
                "erro": (
                    "Não é possível cancelar uma conta "
                    "que já possui pagamentos."
                )
            }

        # --------------------------------------------------------
        # Cancela
        # --------------------------------------------------------

        cursor.execute("""
            UPDATE contas_pagar
            SET status = ?
            WHERE id = ?
        """, (
            STATUS_CANCELADA,
            conta_id
        ))

        conexao.commit()

        return {
            "sucesso": True,
            "id": conta_id,
            "status": STATUS_CANCELADA
        }

    finally:
        conexao.close()


# ============================================================
# TESTE MANUAL
# ============================================================

if __name__ == "__main__":
    print("Módulo de contas a pagar carregado com sucesso.")

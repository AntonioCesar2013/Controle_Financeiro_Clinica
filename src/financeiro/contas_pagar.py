from src.infraestrutura.banco import conectar


# ============================================================
# STATUS
# ============================================================

STATUS_ABERTA = "ABERTA"
STATUS_PARCIAL = "PARCIAL"
STATUS_PAGA = "PAGA"
STATUS_CANCELADA = "CANCELADA"


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

    if valor <= 0:
        return {
            "sucesso": False,
            "erro": "O valor da conta deve ser maior que zero."
        }

    conexao = conectar()
    cursor = conexao.cursor()

    try:

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
                COALESCE((SELECT SUM(p.valor) FROM pagamentos_saida p WHERE p.conta_pagar_id=c.id), 0)

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
                "restante": linha[7] - linha[8] - linha[10],
            }
            for linha in resultados
        ]

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
            SELECT COALESCE(SUM(valor), 0)
            FROM pagamentos_saida
            WHERE conta_pagar_id = ?
        """, (conta_id,))

        total_pago = cursor.fetchone()[0]

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
        status_atual = conta[1]

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

        elif total_pago < valor_conta:
            novo_status = STATUS_PARCIAL

        elif total_pago == valor_conta:
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
            "restante": valor_conta - total_pago,
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

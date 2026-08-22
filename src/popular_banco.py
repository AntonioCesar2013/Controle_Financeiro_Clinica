import sqlite3

from src.banco import CAMINHO_BANCO, conectar, criar_tabelas
from src.cobrancas import gerar_cobrancas, listar_cobrancas
from src.contas_pagar import cadastrar_conta, cancelar_conta
from src.despesas import cadastrar_despesa, cadastrar_setor, cadastrar_tipo_despesa
from src.internacoes import cadastrar_internacao
from src.pagamentos import registrar_pagamento as registrar_pagamento_saida
from src.recebimentos import registrar_pagamento as registrar_recebimento
from src.residentes import cadastrar_residente
from src.responsaveis import cadastrar_responsavel


CENTAVOS = 100


def limpar_banco():
    """Remove os dados de teste, preservando a estrutura do banco."""
    tabelas = [
        "recebimentos", "cobrancas", "internacoes", "residente_responsavel",
        "responsaveis", "residentes", "pagamentos_saida", "contas_pagar",
        "despesas", "tipos_despesa", "setores",
    ]
    conn = sqlite3.connect(CAMINHO_BANCO)
    try:
        for tabela in tabelas:
            conn.execute(f"DELETE FROM {tabela}")
        for tabela in tabelas:
            conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (tabela,))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def _exigir_sucesso(resultado, operacao):
    if "sucesso" in resultado and not resultado["sucesso"]:
        raise RuntimeError(f"{operacao}: {resultado.get('erro', 'falhou.')}")
    return resultado


def cadastrar_residentes():
    dados = [
        ("João da Silva", "11111111111", "Curitiba"),
        ("Carlos Oliveira", "22222222222", "Cascavel"),
        ("Pedro Santos", "33333333333", "Foz do Iguaçu"),
        ("Lucas Ferreira", "44444444444", "Londrina"),
        ("Marcos Souza", "55555555555", "Maringá"),
    ]
    return [cadastrar_residente(*item) for item in dados]


def cadastrar_responsaveis():
    dados = [
        ("Maria da Silva", "66666666666", "(41) 99999-1111", "maria@email.com"),
        ("Ana Oliveira", "77777777777", "(45) 99999-2222", "ana@email.com"),
        ("José Santos", "88888888888", "(45) 99999-3333", "jose@email.com"),
        ("Fernanda Ferreira", "99999999999", "(43) 99999-4444", "fernanda@email.com"),
        ("Paulo Souza", "10101010101", "(44) 99999-5555", "paulo@email.com"),
    ]
    return [cadastrar_responsavel(*item) for item in dados]


def cadastrar_internacoes(residentes, responsaveis):
    dados = [
        ("2026-08-10", 3, 8500, 1000, 2500),
        ("2026-07-15", 4, 9000, 1000, 2000),
        ("2026-08-01", 6, 16000, 1000, 2500),
        ("2026-06-20", 3, 10000, 1000, 3000),
        ("2026-05-05", 5, 17000, 2000, 3000),
    ]
    internacoes = []
    for residente, responsavel, valores in zip(residentes, responsaveis, dados):
        data, periodo, contrato, acolhimento, mensalidade = valores
        resultado = cadastrar_internacao(
            residente_id=residente["id"], responsavel_id=responsavel["id"],
            data_acolhimento=data, periodo_tratamento=periodo,
            valor_contrato=contrato * CENTAVOS,
            valor_acolhimento=acolhimento * CENTAVOS,
            valor_mensalidade=mensalidade * CENTAVOS,
        )
        internacoes.append(_exigir_sucesso(resultado, "Cadastro da internação"))
    return internacoes


def gerar_todas_cobrancas(internacoes):
    for internacao in internacoes:
        _exigir_sucesso(gerar_cobrancas(internacao["id"]), "Geração das cobranças")


def _id_cobranca(internacao_id, numero_parcela):
    for cobranca in listar_cobrancas(internacao_id):
        if cobranca["numero_parcela"] == numero_parcela:
            return cobranca["id"]
    raise RuntimeError("Cobrança de teste não encontrada.")


def _registrar_recebimento(internacao_id, parcela, data, valor_reais, forma, observacao):
    resultado = registrar_recebimento(
        cobranca_id=_id_cobranca(internacao_id, parcela),
        data_pagamento=data, valor=valor_reais * CENTAVOS,
        forma_pagamento=forma, observacao=observacao,
    )
    return _exigir_sucesso(resultado, "Registro de recebimento")


def cadastrar_recebimentos(internacoes):
    joao, carlos, pedro, lucas, marcos = [item["id"] for item in internacoes]
    recebimentos = [
        (joao, 0, "2026-08-10", 1000, "PIX", "Acolhimento"),
        (joao, 1, "2026-09-10", 1000, "PIX", "Mensalidade parcial"),
        (carlos, 0, "2026-07-15", 1000, "DINHEIRO", "Acolhimento"),
        (carlos, 1, "2026-08-15", 2000, "PIX", "Mensalidade 1"),
        (carlos, 2, "2026-09-15", 2000, "TRANSFERENCIA", "Mensalidade 2"),
        (pedro, 0, "2026-08-01", 1000, "DEPOSITO", "Acolhimento"),
        (pedro, 1, "2026-09-01", 1500, "PIX", "Primeira parte da mensalidade"),
        (pedro, 1, "2026-09-05", 1000, "DINHEIRO", "Segunda parte da mensalidade"),
        (lucas, 0, "2026-06-20", 1000, "PIX", "Acolhimento"),
        (marcos, 0, "2026-05-05", 1000, "DINHEIRO", "Acolhimento parcial"),
    ]
    for recebimento in recebimentos:
        _registrar_recebimento(*recebimento)


def cadastrar_financeiro():
    setores = {
        nome: _exigir_sucesso(cadastrar_setor(nome), "Cadastro de setor")["id"]
        for nome in ("Administração", "Cozinha", "Transporte", "Manutenção", "Alojamento")
    }
    tipos = {
        nome: _exigir_sucesso(cadastrar_tipo_despesa(nome), "Cadastro de tipo de despesa")["id"]
        for nome in ("Internet", "Alimentação", "Combustível", "Manutenção", "Energia elétrica", "Água", "Material de limpeza")
    }
    dados_despesas = [
        ("Internet", "Administração", "Internet", "Internet da clínica", "FIXA", True),
        ("Alimentação", "Cozinha", "Alimentação", "Compra de alimentos", "VARIAVEL", True),
        ("Combustível", "Transporte", "Combustível", "Combustível dos veículos", "VARIAVEL", True),
        ("Manutenção", "Manutenção", "Manutenção", "Reparos gerais da clínica", "EXTRAORDINARIA", False),
        ("Energia", "Administração", "Energia elétrica", "Conta de energia elétrica", "FIXA", True),
        ("Água", "Administração", "Água", "Conta de água", "FIXA", True),
    ]
    despesas = {}
    for chave, setor, tipo, descricao, natureza, recorrente in dados_despesas:
        despesas[chave] = _exigir_sucesso(
            cadastrar_despesa(setores[setor], tipos[tipo], descricao, natureza, recorrente),
            "Cadastro de despesa",
        )["id"]

    dados_contas = [
        ("Internet", "2026-09-10", 18000), ("Alimentação", "2026-09-05", 125000),
        ("Combustível", "2026-09-08", 85000), ("Manutenção", "2026-09-15", 230000),
        ("Energia", "2026-09-20", 45000), ("Água", "2026-09-25", 22000),
    ]
    contas = {
        chave: _exigir_sucesso(cadastrar_conta(despesas[chave], vencimento, valor), "Cadastro de conta")["id"]
        for chave, vencimento, valor in dados_contas
    }
    pagamentos_saida = [
        ("Internet", "2026-09-10", 9000, "PIX", "Pagamento parcial"),
        ("Combustível", "2026-09-08", 85000, "DINHEIRO", "Pagamento integral"),
        ("Energia", "2026-09-20", 20000, "PIX", "Primeira parcela"),
        ("Energia", "2026-09-22", 10000, "DINHEIRO", "Segunda parcela"),
    ]
    for chave, data, valor, forma, observacao in pagamentos_saida:
        _exigir_sucesso(
            registrar_pagamento_saida(contas[chave], data, valor, forma, observacao),
            "Registro de pagamento de saída",
        )
    _exigir_sucesso(cancelar_conta(contas["Manutenção"]), "Cancelamento da conta")


def mostrar_resumo(conn):
    print("\n=== RESUMO DE ENTRADAS ===")
    entradas = conn.execute("""
        SELECT r.nome, c.tipo, c.numero_parcela, c.valor, c.desconto,
               COALESCE(SUM(rc.valor), 0), c.status
        FROM cobrancas c
        INNER JOIN internacoes i ON i.id = c.internacao_id
        INNER JOIN residentes r ON r.id = i.residente_id
        LEFT JOIN recebimentos rc ON rc.cobranca_id = c.id
        GROUP BY c.id
        ORDER BY r.id, c.numero_parcela
    """)
    for nome, tipo, parcela, valor, desconto, pago, status in entradas:
        print({"residente": nome, "tipo": tipo, "parcela": parcela,
               "valor_devido": valor - desconto, "total_recebido": pago, "status": status})

    print("\n=== RESUMO DE SAÍDAS ===")
    saidas = conn.execute("""
        SELECT d.descricao, cp.data_vencimento, cp.valor,
               COALESCE(SUM(ps.valor), 0), cp.status
        FROM contas_pagar cp
        INNER JOIN despesas d ON d.id = cp.despesa_id
        LEFT JOIN pagamentos_saida ps ON ps.conta_pagar_id = cp.id
        GROUP BY cp.id
        ORDER BY cp.id
    """)
    for descricao, vencimento, valor, pago, status in saidas:
        print({"despesa": descricao, "vencimento": vencimento, "valor": valor,
               "total_pago": pago, "restante": valor - pago, "status": status})


def popular_banco():
    criar_tabelas()
    conn = conectar()
    try:
        limpar_banco()
        residentes = cadastrar_residentes()
        responsaveis = cadastrar_responsaveis()
        internacoes = cadastrar_internacoes(residentes, responsaveis)
        gerar_todas_cobrancas(internacoes)
        cadastrar_recebimentos(internacoes)
        cadastrar_financeiro()
        mostrar_resumo(conn)
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("\n=== BANCO POPULADO COM SUCESSO ===")


if __name__ == "__main__":
    popular_banco()

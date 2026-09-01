"""Relatórios institucionais das áreas controladas pelo sistema."""

from datetime import date, datetime
import sqlite3

from src import caixa
from src.banco import conectar


TIPOS = {
    "financeiro": "Financeiro - fluxo de caixa",
    "despesas_setor": "Despesas por setor",
    "internacoes": "Internações",
    "residentes": "Residentes",
    "cantina": "Cantina - vendas",
    "carteiras": "Carteiras dos residentes",
    "estoque": "Estoque da Cantina",
    "colaboradores": "Colaboradores",
}


def _periodo(inicio, fim):
    inicio = inicio or f"{date.today().year:04d}-{date.today().month:02d}-01"
    fim = fim or date.today().isoformat()
    try:
        if date.fromisoformat(inicio) > date.fromisoformat(fim):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("O período informado é inválido.")
    return inicio, fim


def _consulta(sql, parametros=()):
    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        return [dict(x) for x in conn.execute(sql, parametros).fetchall()]
    finally:
        conn.close()


def gerar(tipo, data_inicio=None, data_fim=None):
    if tipo not in TIPOS:
        raise ValueError("Tipo de relatório inválido.")
    inicio, fim = _periodo(data_inicio, data_fim)
    resumo = []
    colunas = []
    linhas = []
    usa_periodo = tipo in {"financeiro", "despesas_setor", "internacoes", "cantina"}

    if tipo == "financeiro":
        dados = caixa.resumo_caixa(inicio, fim)
        linhas = caixa.listar_movimentacoes(inicio, fim)
        resumo = [("Entradas", dados["total_entradas"], "centavos"),
                  ("Saídas", dados["total_saidas"], "centavos"),
                  ("Resultado", dados["resultado"], "centavos")]
        colunas = [("Data", "data", "data"), ("Descrição", "descricao", "texto"),
                   ("Tipo", "tipo", "texto"), ("Forma", "forma_pagamento", "texto"),
                   ("Valor", "valor", "centavos")]
    elif tipo == "despesas_setor":
        linhas = _consulta(
            """SELECT s.nome AS setor, COUNT(cp.id) AS quantidade,
                      COALESCE(SUM(cp.valor),0) AS total_previsto,
                      COALESCE(SUM((SELECT SUM(ps.valor) FROM pagamentos_saida ps WHERE ps.conta_pagar_id=cp.id)),0) AS total_pago
               FROM setores s LEFT JOIN despesas d ON d.setor_id=s.id
               LEFT JOIN contas_pagar cp ON cp.despesa_id=d.id AND cp.data_vencimento BETWEEN ? AND ?
               GROUP BY s.id ORDER BY s.nome""", (inicio, fim))
        resumo = [("Setores", len(linhas), "numero"),
                  ("Total pago", sum(x["total_pago"] for x in linhas), "centavos")]
        colunas = [("Setor", "setor", "texto"), ("Lançamentos", "quantidade", "numero"),
                   ("Total previsto", "total_previsto", "centavos"),
                   ("Total pago", "total_pago", "centavos")]
    elif tipo == "internacoes":
        linhas = _consulta(
            """SELECT r.nome AS residente_nome, rp.nome AS responsavel_nome,
                      i.data_acolhimento, i.periodo_tratamento, i.valor_contrato, i.status
               FROM internacoes i JOIN residentes r ON r.id=i.residente_id
               JOIN responsaveis rp ON rp.id=i.responsavel_id
               WHERE i.data_acolhimento BETWEEN ? AND ? ORDER BY i.data_acolhimento, r.nome""",
            (inicio, fim))
        resumo = [("Internações no período", len(linhas), "numero")]
        colunas = [("Residente", "residente_nome", "texto"), ("Responsável", "responsavel_nome", "texto"),
                   ("Acolhimento", "data_acolhimento", "data"), ("Período", "periodo_tratamento", "numero"),
                   ("Contrato", "valor_contrato", "centavos"), ("Status", "status", "texto")]
    elif tipo == "residentes":
        linhas = _consulta("SELECT nome,cpf,cidade_origem,ativo FROM residentes ORDER BY nome")
        resumo = [("Residentes", len(linhas), "numero"),
                  ("Ativos", sum(1 for x in linhas if x["ativo"]), "numero")]
        colunas = [("Nome", "nome", "texto"), ("CPF", "cpf", "cpf"),
                   ("Cidade de origem", "cidade_origem", "texto"), ("Situação", "ativo", "ativo")]
    elif tipo == "cantina":
        linhas = _consulta(
            """SELECT m.data_movimentacao, r.nome AS residente_nome, i.nome AS item_nome,
                      m.quantidade, iv.valor AS valor_unitario, m.valor_total
               FROM movimentacoes_carteira m JOIN carteiras c ON c.id=m.carteira_id
               JOIN residentes r ON r.id=c.residente_id JOIN itens i ON i.id=m.item_id
               JOIN itens_valores iv ON iv.id=m.item_valor_id
               WHERE m.tipo='COMPRA_CANTINA' AND m.estornada=0
                 AND m.data_movimentacao BETWEEN ? AND ?
               ORDER BY m.data_movimentacao, m.id""", (inicio, fim))
        resumo = [("Vendas", len(linhas), "numero"),
                  ("Total vendido", sum(x["valor_total"] for x in linhas), "reais")]
        colunas = [("Data", "data_movimentacao", "data"), ("Residente", "residente_nome", "texto"),
                   ("Produto", "item_nome", "texto"), ("Qtd.", "quantidade", "numero"),
                   ("Unitário", "valor_unitario", "reais"), ("Total", "valor_total", "reais")]
    elif tipo == "carteiras":
        linhas = _consulta(
            """SELECT r.nome AS residente_nome, c.saldo, c.ativo,
                      COUNT(CASE WHEN m.tipo='COMPRA_CANTINA' AND m.estornada=0 THEN 1 END) AS compras,
                      COALESCE(SUM(CASE WHEN m.tipo='COMPRA_CANTINA' AND m.estornada=0 THEN m.valor_total ELSE 0 END),0) AS total_compras
               FROM carteiras c JOIN residentes r ON r.id=c.residente_id
               LEFT JOIN movimentacoes_carteira m ON m.carteira_id=c.id
               GROUP BY c.id ORDER BY r.nome""")
        resumo = [("Carteiras", len(linhas), "numero"),
                  ("Saldo total", sum(x["saldo"] for x in linhas), "reais")]
        colunas = [("Residente", "residente_nome", "texto"), ("Saldo", "saldo", "reais"),
                   ("Compras", "compras", "numero"), ("Total consumido", "total_compras", "reais"),
                   ("Situação", "ativo", "ativo")]
    elif tipo == "estoque":
        linhas = _consulta(
            """SELECT i.nome, i.categoria, i.unidade_medida, i.estoque_atual, i.estoque_minimo,
                      (SELECT iv.valor FROM itens_valores iv WHERE iv.item_id=i.id AND iv.ativo=1
                       ORDER BY iv.data_inicio_valor DESC, iv.id DESC LIMIT 1) AS valor_atual,
                      CASE WHEN UPPER(i.categoria) IN ('SERVIÇO','SERVIÇOS','SERVICO','SERVICOS') THEN 'NÃO SE APLICA'
                           WHEN i.estoque_atual<=i.estoque_minimo THEN 'REPOR' ELSE 'OK' END AS situacao_estoque,
                      i.ativo FROM itens i ORDER BY i.nome""")
        resumo = [("Produtos", len(linhas), "numero"),
                  ("Precisam de reposição", sum(1 for x in linhas if x["ativo"] == 1 and x["situacao_estoque"] == "REPOR"), "numero")]
        colunas = [("Produto", "nome", "texto"), ("Categoria", "categoria", "texto"),
                   ("Un.", "unidade_medida", "texto"), ("Estoque", "estoque_atual", "numero"),
                   ("Mínimo", "estoque_minimo", "numero"), ("Preço", "valor_atual", "reais"),
                   ("Estoque", "situacao_estoque", "texto")]
    elif tipo == "colaboradores":
        linhas = _consulta("SELECT nome,cpf,status,criado_em FROM colaboradores ORDER BY nome")
        resumo = [("Colaboradores", len(linhas), "numero"),
                  ("Ativos", sum(1 for x in linhas if x["status"] == "ATIVO"), "numero")]
        colunas = [("Nome", "nome", "texto"), ("CPF", "cpf", "cpf"),
                   ("Status", "status", "texto"), ("Cadastrado em", "criado_em", "data_hora")]

    return {"tipo": tipo, "titulo": TIPOS[tipo], "usa_periodo": usa_periodo,
            "data_inicio": inicio, "data_fim": fim, "emitido_em": datetime.now().isoformat(timespec="minutes"),
            "resumo": [{"rotulo": x[0], "valor": x[1], "formato": x[2]} for x in resumo],
            "colunas": [{"rotulo": x[0], "campo": x[1], "formato": x[2]} for x in colunas],
            "linhas": linhas}

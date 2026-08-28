"""Consultas e cálculos do fluxo de caixa da clínica.

O módulo não mantém uma tabela própria: cada movimentação é obtida diretamente
dos recebimentos e pagamentos de saída já registrados no banco.
"""

from datetime import date, datetime, timedelta
import sqlite3

from src.banco import conectar


def _validar_data(data_texto, nome="data"):
    """Valida e devolve uma data ISO no formato ``YYYY-MM-DD``."""
    if not isinstance(data_texto, str):
        raise ValueError(f"{nome.capitalize()} deve estar no formato YYYY-MM-DD.")

    try:
        data_convertida = datetime.strptime(data_texto, "%Y-%m-%d").date()
    except ValueError as erro:
        raise ValueError(
            f"{nome.capitalize()} deve estar no formato YYYY-MM-DD."
        ) from erro

    if data_convertida.isoformat() != data_texto:
        raise ValueError(f"{nome.capitalize()} deve estar no formato YYYY-MM-DD.")

    return data_convertida


def _periodo_validado(data_inicio=None, data_fim=None):
    """Valida os limites opcionais de uma consulta."""
    inicio = _validar_data(data_inicio, "data inicial") if data_inicio is not None else None
    fim = _validar_data(data_fim, "data final") if data_fim is not None else None

    if inicio and fim and inicio > fim:
        raise ValueError("A data inicial não pode ser posterior à data final.")

    return (
        inicio.isoformat() if inicio else None,
        fim.isoformat() if fim else None,
    )


def listar_movimentacoes(data_inicio=None, data_fim=None):
    """Lista entradas e saídas efetivamente realizadas no período informado.

    Valores são inteiros em centavos. Para entradas, ``origem_id`` é o ID da
    cobrança; para saídas, é o ID da conta a pagar.
    """
    data_inicio, data_fim = _periodo_validado(data_inicio, data_fim)
    filtros_entrada = []
    filtros_bancarias = []
    filtros_saida = []
    parametros_entrada = []
    parametros_bancarias = []
    parametros_saida = []

    if data_inicio:
        filtros_entrada.append("r.data_recebimento >= ?")
        filtros_bancarias.append("eb.data_entrada >= ?")
        filtros_saida.append("ps.data_pagamento >= ?")
        parametros_entrada.append(data_inicio)
        parametros_bancarias.append(data_inicio)
        parametros_saida.append(data_inicio)
    if data_fim:
        filtros_entrada.append("r.data_recebimento <= ?")
        filtros_bancarias.append("eb.data_entrada <= ?")
        filtros_saida.append("ps.data_pagamento <= ?")
        parametros_entrada.append(data_fim)
        parametros_bancarias.append(data_fim)
        parametros_saida.append(data_fim)

    where_entrada = " WHERE " + " AND ".join(filtros_entrada) if filtros_entrada else ""
    where_bancarias = " WHERE " + " AND ".join(filtros_bancarias) if filtros_bancarias else ""
    where_saida = " WHERE " + " AND ".join(filtros_saida) if filtros_saida else ""

    conexao = conectar()
    conexao.row_factory = sqlite3.Row
    try:
        entradas = conexao.execute(
            f"""
            SELECT
                r.id,
                r.data_recebimento AS data,
                r.valor,
                r.forma_recebimento AS forma_pagamento,
                r.observacao,
                r.cobranca_id AS origem_id,
                res.nome AS residente_nome,
                c.tipo AS cobranca_tipo,
                c.numero_parcela AS numero_parcela
            FROM recebimentos r
            INNER JOIN cobrancas c ON c.id = r.cobranca_id
            INNER JOIN internacoes i ON i.id = c.internacao_id
            INNER JOIN residentes res ON res.id = i.residente_id
            {where_entrada}
            """,
            parametros_entrada,
        ).fetchall()
        entradas_bancarias = conexao.execute(
            f"""
            SELECT eb.id, eb.data_entrada AS data, eb.valor,
                   eb.forma_recebimento AS forma_pagamento, eb.descricao,
                   eb.observacao
            FROM entradas_bancarias eb
            {where_bancarias}
            """,
            parametros_bancarias,
        ).fetchall()
        saidas = conexao.execute(
            f"""
            SELECT
                ps.id,
                ps.data_pagamento AS data,
                ps.valor,
                ps.forma_pagamento,
                ps.observacao,
                ps.conta_pagar_id AS origem_id,
                d.descricao,
                s.nome AS setor,
                td.nome AS tipo_despesa
            FROM pagamentos_saida ps
            INNER JOIN contas_pagar cp ON cp.id = ps.conta_pagar_id
            INNER JOIN despesas d ON d.id = cp.despesa_id
            INNER JOIN setores s ON s.id = d.setor_id
            INNER JOIN tipos_despesa td ON td.id = d.tipo_despesa_id
            {where_saida}
            """,
            parametros_saida,
        ).fetchall()
    finally:
        conexao.close()

    movimentacoes = []
    for entrada in entradas:
        movimentacoes.append({
            "id": entrada["id"],
            "data": entrada["data"],
            "tipo": "ENTRADA",
            "descricao": (
                f"Recebimento de {entrada['residente_nome']} - "
                f"{entrada['cobranca_tipo']} parcela {entrada['numero_parcela']}"
            ),
            "valor": entrada["valor"],
            "forma_pagamento": entrada["forma_pagamento"],
            "origem_id": entrada["origem_id"],
            "residente_nome": entrada["residente_nome"],
            "cobranca_tipo": entrada["cobranca_tipo"],
            "numero_parcela": entrada["numero_parcela"],
            "observacao": entrada["observacao"],
        })
    for entrada in entradas_bancarias:
        movimentacoes.append({
            "id": entrada["id"], "data": entrada["data"], "tipo": "ENTRADA",
            "descricao": entrada["descricao"], "valor": entrada["valor"],
            "forma_pagamento": entrada["forma_pagamento"], "origem_id": entrada["id"],
            "observacao": entrada["observacao"],
        })
    for saida in saidas:
        movimentacoes.append({
            "id": saida["id"],
            "data": saida["data"],
            "tipo": "SAIDA",
            "descricao": saida["descricao"],
            "valor": saida["valor"],
            "forma_pagamento": saida["forma_pagamento"],
            "origem_id": saida["origem_id"],
            "setor": saida["setor"],
            "tipo_despesa": saida["tipo_despesa"],
            "observacao": saida["observacao"],
        })

    return sorted(movimentacoes, key=lambda movimento: (movimento["data"], movimento["id"]))


def _resumo(data_inicio=None, data_fim=None, incluir_movimentacoes=False):
    movimentacoes = listar_movimentacoes(data_inicio, data_fim)
    total_entradas = sum(m["valor"] for m in movimentacoes if m["tipo"] == "ENTRADA")
    total_saidas = sum(m["valor"] for m in movimentacoes if m["tipo"] == "SAIDA")
    resumo = {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "resultado": total_entradas - total_saidas,
    }
    if incluir_movimentacoes:
        resumo["movimentacoes"] = movimentacoes
    return resumo


def resumo_caixa(data_inicio=None, data_fim=None):
    """Retorna os totais de entradas, saídas e resultado do período."""
    data_inicio, data_fim = _periodo_validado(data_inicio, data_fim)
    return _resumo(data_inicio, data_fim)


def resumo_diario(data):
    """Retorna o resumo e as movimentações de um único dia."""
    data = _validar_data(data).isoformat()
    return _resumo(data, data, incluir_movimentacoes=True)


def resumo_semanal(data):
    """Retorna o resumo de segunda-feira a domingo da semana da data."""
    data_referencia = _validar_data(data)
    inicio = data_referencia - timedelta(days=data_referencia.weekday())
    fim = inicio + timedelta(days=6)
    return _resumo(inicio.isoformat(), fim.isoformat(), incluir_movimentacoes=True)


def _periodo_mensal(ano, mes):
    try:
        inicio = date(int(ano), int(mes), 1)
    except (TypeError, ValueError) as erro:
        raise ValueError("Ano e mês devem formar uma data válida.") from erro
    fim = date(inicio.year + (inicio.month == 12), inicio.month % 12 + 1, 1) - timedelta(days=1)
    return inicio, fim


def resumo_mensal(ano, mes):
    """Retorna os totais do mês informado."""
    inicio, fim = _periodo_mensal(ano, mes)
    return _resumo(inicio.isoformat(), fim.isoformat())


def resumo_anual(ano):
    """Retorna os totais do ano informado."""
    try:
        ano = int(ano)
        inicio = date(ano, 1, 1)
        fim = date(ano, 12, 31)
    except (TypeError, ValueError) as erro:
        raise ValueError("Ano deve ser válido.") from erro
    return _resumo(inicio.isoformat(), fim.isoformat())


def resumo_periodo(data_inicio, data_fim):
    """Retorna os totais de um período inclusivo informado pelo usuário."""
    return resumo_caixa(data_inicio, data_fim)


def saldo_acumulado(data=None):
    """Retorna o saldo de todas as movimentações até a data informada."""
    data_final = _validar_data(data).isoformat() if data is not None else date.today().isoformat()
    resumo = resumo_caixa(data_fim=data_final)
    return resumo["resultado"]


def resumo_mensal_detalhado(ano, mes):
    """Agrupa o fluxo do mês por dia, incluindo dias sem movimentação."""
    inicio, fim = _periodo_mensal(ano, mes)
    totais = {}
    for movimento in listar_movimentacoes(inicio.isoformat(), fim.isoformat()):
        dia = totais.setdefault(movimento["data"], {"entradas": 0, "saidas": 0})
        chave = "entradas" if movimento["tipo"] == "ENTRADA" else "saidas"
        dia[chave] += movimento["valor"]

    resultado = []
    dia_atual = inicio
    while dia_atual <= fim:
        data_atual = dia_atual.isoformat()
        valores = totais.get(data_atual, {"entradas": 0, "saidas": 0})
        resultado.append({
            "data": data_atual,
            "entradas": valores["entradas"],
            "saidas": valores["saidas"],
            "resultado": valores["entradas"] - valores["saidas"],
        })
        dia_atual += timedelta(days=1)
    return resultado


def resumo_anual_detalhado(ano):
    """Agrupa o fluxo do ano por mês, incluindo meses sem movimentação."""
    try:
        ano = int(ano)
        date(ano, 1, 1)
    except (TypeError, ValueError) as erro:
        raise ValueError("Ano deve ser válido.") from erro

    totais = {mes: {"entradas": 0, "saidas": 0} for mes in range(1, 13)}
    for movimento in listar_movimentacoes(f"{ano:04d}-01-01", f"{ano:04d}-12-31"):
        valores = totais[date.fromisoformat(movimento["data"]).month]
        chave = "entradas" if movimento["tipo"] == "ENTRADA" else "saidas"
        valores[chave] += movimento["valor"]

    return [
        {
            "mes": mes,
            "entradas": totais[mes]["entradas"],
            "saidas": totais[mes]["saidas"],
            "resultado": totais[mes]["entradas"] - totais[mes]["saidas"],
        }
        for mes in range(1, 13)
    ]

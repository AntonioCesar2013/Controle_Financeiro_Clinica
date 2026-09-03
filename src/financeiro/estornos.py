"""Preserva integralmente lançamentos retirados dos totais financeiros."""
import json
from src.infraestrutura.banco import conectar


def preservar(conexao, tabela, lancamento_id, motivo):
    if tabela not in {"recebimentos", "pagamentos_saida"}:
        raise ValueError("Origem de estorno inválida.")
    cursor = conexao.execute(f"SELECT * FROM {tabela} WHERE id=?", (lancamento_id,))
    linha = cursor.fetchone()
    if linha is None:
        raise ValueError("Lançamento não encontrado.")
    dados = dict(zip([coluna[0] for coluna in cursor.description], linha))
    origem = dados.get("cobranca_id", dados.get("conta_pagar_id"))
    conexao.execute(
        """INSERT INTO estornos_financeiros(tabela,lancamento_id,origem_id,dados,motivo)
           VALUES(?,?,?,?,?)""",
        (tabela, lancamento_id, origem, json.dumps(dados, ensure_ascii=False),
         str(motivo or "Estorno solicitado pelo operador").strip()),
    )


def historico(tabela, origem_id, ativos):
    conexao = conectar()
    try:
        estornados = [{**json.loads(dados), "estornada": True,
                      "estornada_em": quando, "motivo_estorno": motivo}
                     for dados, quando, motivo in conexao.execute(
                         "SELECT dados,estornada_em,motivo FROM estornos_financeiros WHERE tabela=? AND origem_id=?",
                         (tabela, origem_id))]
        return [{**item, "estornada": False} for item in ativos] + estornados
    finally:
        conexao.close()


def historico_ajustes(cobranca_id):
    conexao = conectar()
    try:
        cursor = conexao.execute(
            "SELECT * FROM ajustes_cobrancas WHERE cobranca_id=? ORDER BY id", (cobranca_id,)
        )
        nomes = [coluna[0] for coluna in cursor.description]
        return [dict(zip(nomes, linha)) for linha in cursor.fetchall()]
    finally:
        conexao.close()

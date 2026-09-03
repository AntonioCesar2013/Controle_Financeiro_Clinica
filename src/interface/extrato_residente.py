"""Consulta consolidada do residente sem misturar caixa com carteira."""
import sqlite3
from datetime import date
from src.infraestrutura.banco import conectar
from src.financeiro.caixa import _periodo_validado
from src.financeiro.contas_receber import listar_cobrancas_consolidadas
from src.financeiro.estornos import historico


def consultar(residente_id, inicio=None, fim=None):
    inicio, fim = _periodo_validado(inicio, fim)
    def no_periodo(data):
        return (not inicio or data >= inicio) and (not fim or data <= fim)
    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        residente = conn.execute("SELECT id,nome,cpf,cidade_origem FROM residentes WHERE id=?", (residente_id,)).fetchone()
        if not residente:
            raise ValueError("Residente não encontrado.")
        internacoes = [dict(r) for r in conn.execute(
            """SELECT i.*,rp.nome AS responsavel_nome FROM internacoes i
               JOIN responsaveis rp ON rp.id=i.responsavel_id WHERE i.residente_id=? ORDER BY i.data_acolhimento DESC""", (residente_id,))]
        todas = []
        pagamentos = []
        for internacao in internacoes:
            for c in listar_cobrancas_consolidadas(internacao["id"]):
                todas.append(c)
                ativos = [dict(r) for r in conn.execute("SELECT * FROM recebimentos WHERE cobranca_id=?", (c["id"],))]
                pagamentos.extend({**r, "numero_parcela": c["numero_parcela"], "tipo": c["tipo"]}
                                  for r in historico("recebimentos", c["id"], ativos) if no_periodo(r["data_recebimento"]))
        cobrancas = [c for c in todas if no_periodo(c["data_vencimento"])]
        carteira = conn.execute("SELECT id,saldo FROM carteiras WHERE residente_id=?", (residente_id,)).fetchone()
        movimentos, saldo_abertura, saldo_fechamento = [], 0, 0
        if carteira:
            todos_mov = [dict(r) for r in conn.execute(
                """SELECT m.*,i.nome AS item_nome FROM movimentacoes_carteira m
                   LEFT JOIN itens i ON i.id=m.item_id WHERE carteira_id=? ORDER BY data_movimentacao,m.id""", (carteira["id"],))]
            def efeito(m):
                if m["estornada"]:
                    return 0
                # Registros de importadores antigos usavam COMPRA com valor negativo.
                if m["tipo"] == "COMPRA":
                    return -abs(m["valor_total"])
                return m["valor_total"] if m["tipo"] == "CREDITO" else -m["valor_total"]
            saldo = carteira["saldo"] - sum(efeito(m) for m in todos_mov)
            saldo += sum(efeito(m) for m in todos_mov if inicio and m["data_movimentacao"] < inicio)
            saldo_abertura = saldo
            for m in todos_mov:
                if no_periodo(m["data_movimentacao"]):
                    saldo += efeito(m)
                    movimentos.append({**m, "saldo_apos": saldo})
            saldo_fechamento = saldo
        return {
            "residente": dict(residente), "internacoes": internacoes, "data_inicio": inicio, "data_fim": fim,
            "cobrancas": cobrancas, "recebimentos": sorted(pagamentos, key=lambda r: (r["data_recebimento"], r["id"])),
            "movimentacoes_carteira": movimentos,
            "resumo": {"devido_periodo": sum(c["valor_devido"] for c in cobrancas),
                       "recebido_periodo": sum(r["valor"] for r in pagamentos if not r["estornada"]),
                       "pendente_periodo": sum(c["saldo_restante"] for c in cobrancas),
                       "pendente_total": sum(c["saldo_restante"] for c in todas),
                       "carteira_atual": carteira["saldo"] if carteira else 0,
                       "carteira_abertura": saldo_abertura, "carteira_fechamento": saldo_fechamento},
            "emitido_em": date.today().isoformat(),
        }
    finally:
        conn.close()

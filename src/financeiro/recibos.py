"""Recibos numerados de recebimentos de mensalidade, com dados preservados."""
import json
import sqlite3
from src.infraestrutura.banco import conectar


def gerar(recebimento_id):
    conn = conectar()
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        dados = conn.execute(
            """SELECT r.*,c.tipo,c.numero_parcela,c.data_vencimento,c.valor-c.desconto AS valor_devido,
                      i.id AS internacao_id,res.nome AS residente_nome,res.cpf AS residente_cpf,
                      rp.nome AS responsavel_nome,rp.cpf AS responsavel_cpf,
                      COALESCE((SELECT SUM(valor) FROM recebimentos WHERE cobranca_id=c.id),0) AS total_recebido
               FROM recebimentos r JOIN cobrancas c ON c.id=r.cobranca_id
               JOIN internacoes i ON i.id=c.internacao_id JOIN residentes res ON res.id=i.residente_id
               JOIN responsaveis rp ON rp.id=i.responsavel_id WHERE r.id=?""", (recebimento_id,)
        ).fetchone()
        if not dados or dados["tipo"] != "MENSALIDADE":
            raise ValueError("Selecione um recebimento efetivo de mensalidade para gerar o recibo.")
        conn.execute("INSERT OR IGNORE INTO recibos(recebimento_id,dados) VALUES(?,?)",
                     (recebimento_id, json.dumps(dict(dados), ensure_ascii=False)))
        recibo_id = conn.execute("SELECT id FROM recibos WHERE recebimento_id=?", (recebimento_id,)).fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return consultar(recibo_id)


def consultar(recibo_id):
    conn = conectar()
    try:
        registro = conn.execute(
            """SELECT id,recebimento_id,dados,emitido_em,
                      EXISTS(SELECT 1 FROM recebimentos r WHERE r.id=recibos.recebimento_id)
               FROM recibos WHERE id=?""", (recibo_id,)
        ).fetchone()
        if not registro:
            raise ValueError("Recibo não encontrado.")
        return {"id": registro[0], "numero": f"REC-{registro[0]:06d}",
                "recebimento_id": registro[1], "dados": json.loads(registro[2]),
                "emitido_em": registro[3], "cancelado": not bool(registro[4])}
    finally:
        conn.close()

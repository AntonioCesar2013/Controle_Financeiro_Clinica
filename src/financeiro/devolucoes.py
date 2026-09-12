"""Devolução efetiva, mantendo recibo e entrada originais."""
from contextlib import closing
from datetime import date
import sqlite3

from src.infraestrutura.banco import conectar
from src.financeiro.moeda import validar_centavos


def registrar(recebimento_id, valor, data_devolucao, forma_pagamento, motivo, documento, multa_juros=0):
    valor = validar_centavos(valor)
    multa_juros = validar_centavos(multa_juros)
    try:
        data = date.fromisoformat(data_devolucao)
        if data.isoformat() != data_devolucao or data > date.today():
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('Informe uma data de devolução válida e não futura.')
    if valor < 0 or multa_juros < 0 or valor + multa_juros <= 0:
        raise ValueError('Informe valores não negativos e um total de devolução positivo.')
    if any(not isinstance(x, str) or not x.strip() for x in (forma_pagamento, motivo, documento)):
        raise ValueError('Informe a forma, o motivo e o comprovante da devolução realizada.')
    with closing(conectar()) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.execute('BEGIN IMMEDIATE')
        recebido = conn.execute('SELECT * FROM recebimentos_liquidos WHERE id=?', (recebimento_id,)).fetchone()
        if not recebido:
            raise ValueError('Recebimento não encontrado.')
        if data_devolucao < recebido['data_recebimento']:
            raise ValueError('A devolução não pode anteceder o recebimento.')
        if valor > recebido['valor']:
            raise ValueError('A devolução excede o principal ainda disponível deste recebimento.')
        if multa_juros > recebido['multa_juros']:
            raise ValueError('A devolução excede as multas e juros ainda disponíveis deste recebimento.')
        cur = conn.execute('''INSERT INTO devolucoes_recebimentos
            (recebimento_id,valor,data_devolucao,forma_pagamento,motivo,documento,multa_juros) VALUES(?,?,?,?,?,?,?)''',
            (recebimento_id, valor, data_devolucao, forma_pagamento.strip(), motivo.strip(), documento.strip(), multa_juros))
        cid = recebido['cobranca_id']
        devido = conn.execute('SELECT valor-desconto FROM cobrancas WHERE id=?', (cid,)).fetchone()[0]
        total = conn.execute('SELECT COALESCE(SUM(valor),0) FROM recebimentos_liquidos WHERE cobranca_id=?', (cid,)).fetchone()[0]
        status = 'DESCONTADA' if devido == 0 else 'PAGA' if total == devido else 'PARCIAL' if total else 'ABERTA'
        conn.execute('UPDATE cobrancas SET status=? WHERE id=?', (status, cid))
        return {'sucesso': True, 'id': cur.lastrowid, 'cobranca_id': cid, 'valor': valor,
                'multa_juros': multa_juros, 'total_lancamento': valor+multa_juros,
                'total_recebido': total, 'saldo_restante': devido-total, 'status': status}


def listar(cobranca_id=None):
    with closing(conectar()) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute('''SELECT d.*,d.valor+d.multa_juros AS total_lancamento,r.cobranca_id FROM devolucoes_recebimentos d
            JOIN recebimentos r ON r.id=d.recebimento_id
            WHERE (? IS NULL OR r.cobranca_id=?) ORDER BY d.data_devolucao,d.id''', (cobranca_id, cobranca_id))]


def estornar(devolucao_id, motivo):
    """Corrige registro indevido; não representa uma nova entrada de dinheiro."""
    if not isinstance(motivo, str) or not motivo.strip():
        raise ValueError('Informe o motivo do estorno da devolução lançada por engano.')
    with closing(conectar()) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.execute('BEGIN IMMEDIATE')
        d = conn.execute('''SELECT d.*,r.cobranca_id FROM devolucoes_recebimentos d
            JOIN recebimentos r ON r.id=d.recebimento_id WHERE d.id=?''', (devolucao_id,)).fetchone()
        if not d or d['estornada']:
            raise ValueError('Devolução não encontrada ou já estornada.')
        cid = d['cobranca_id']
        devido = conn.execute('SELECT valor-desconto FROM cobrancas WHERE id=?', (cid,)).fetchone()[0]
        total = conn.execute('SELECT COALESCE(SUM(valor),0) FROM recebimentos_liquidos WHERE cobranca_id=?', (cid,)).fetchone()[0] + d['valor']
        if total > devido:
            raise ValueError('O estorno excederia o valor devido da cobrança. É necessário revisar explicitamente o acerto contratual ou os recebimentos posteriores; nenhuma alteração foi salva.')
        conn.execute('''UPDATE devolucoes_recebimentos SET estornada=1,estornada_em=CURRENT_TIMESTAMP,
            motivo_estorno=? WHERE id=?''', (motivo.strip(), devolucao_id))
        status = 'DESCONTADA' if devido == 0 else 'PAGA' if total == devido else 'PARCIAL' if total else 'ABERTA'
        conn.execute('UPDATE cobrancas SET status=? WHERE id=?', (status, cid))
        return {'sucesso': True, 'id': devolucao_id, 'cobranca_id': cid, 'status': status, 'total_recebido': total, 'saldo_restante': devido-total}

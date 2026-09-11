"""Identifica entradas bancárias sem lançar dinheiro pela segunda vez.

A entrada bancária é a referência de data do caixa quando vinculada a
recebimentos. Créditos das carteiras permanecem em controle separado.
"""
import json
import sqlite3
from contextlib import closing

from src.infraestrutura.banco import conectar


def texto_obrigatorio(valor, nome):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f'Informe {nome}.')
    if len(valor.strip()) > 2000:
        raise ValueError(f'{nome.capitalize()} deve ter no máximo 2000 caracteres.')
    return valor.strip()


def listar(conn):
    return [dict(r) for r in conn.execute("""
        SELECT eb.*, cb.id AS conciliacao_id, COALESCE(cb.destino,'PENDENTE') AS destino,
               cb.motivo, cb.vinculos_originais
        FROM entradas_bancarias eb LEFT JOIN conciliacoes_bancarias cb
          ON cb.entrada_id=eb.id AND cb.desfeita_em IS NULL
        ORDER BY eb.data_entrada DESC,eb.id DESC""")]


def painel():
    with closing(conectar()) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('BEGIN')
        return {
            'entradas': listar(conn),
            'recebimentos': [dict(r) for r in conn.execute("""
                SELECT r.id,r.valor + COALESCE(r.multa_juros,0) AS valor,
                       r.valor AS valor_principal,r.multa_juros,
                       r.data_recebimento AS data,res.nome,c.numero_parcela
                FROM recebimentos r JOIN cobrancas c ON c.id=r.cobranca_id
                JOIN internacoes i ON i.id=c.internacao_id JOIN residentes res ON res.id=i.residente_id
                WHERE NOT EXISTS(SELECT 1 FROM conciliacoes_vinculos v WHERE v.recebimento_id=r.id)
                ORDER BY r.data_recebimento DESC,r.id DESC""")],
            'creditos': [dict(r) for r in conn.execute("""
                SELECT m.id,m.valor_total AS valor,m.data_movimentacao AS data,r.nome
                FROM movimentacoes_carteira m JOIN carteiras c ON c.id=m.carteira_id
                JOIN residentes r ON r.id=c.residente_id
                WHERE m.tipo='CREDITO' AND m.estornada=0
                AND NOT EXISTS(SELECT 1 FROM conciliacoes_vinculos v WHERE v.movimento_id=m.id)
                ORDER BY m.data_movimentacao DESC,m.id DESC""")],
            'historico': [dict(r) for r in conn.execute(
                'SELECT * FROM conciliacoes_bancarias ORDER BY id DESC')],
        }


def conciliar(entrada_id, destino, ids, motivo):
    motivo = texto_obrigatorio(motivo, 'a identificação do documento ou o motivo')
    if destino not in ('RECEBIMENTO', 'CARTEIRA', 'OUTRA_RECEITA'):
        raise ValueError('Destino da entrada inválido.')
    if not isinstance(ids, list) or any(type(i) is not int or i <= 0 for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('Selecione lançamentos válidos, sem repetição.')
    if (destino == 'OUTRA_RECEITA' and ids) or (destino != 'OUTRA_RECEITA' and not ids):
        raise ValueError('Selecione os lançamentos correspondentes ao destino.')
    with closing(conectar()) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.execute('BEGIN IMMEDIATE')
        entrada = conn.execute('SELECT * FROM entradas_bancarias WHERE id=?', (entrada_id,)).fetchone()
        if not entrada:
            raise ValueError('Entrada bancária não encontrada.')
        if conn.execute('SELECT 1 FROM conciliacoes_bancarias WHERE entrada_id=? AND desfeita_em IS NULL', (entrada_id,)).fetchone():
            raise ValueError('Esta entrada já está conciliada. Desfaça o vínculo para corrigir.')
        registros = []
        coluna = 'recebimento_id' if destino == 'RECEBIMENTO' else 'movimento_id'
        for identificador in ids:
            if conn.execute(f'SELECT 1 FROM conciliacoes_vinculos WHERE {coluna}=?', (identificador,)).fetchone():
                raise ValueError('Um dos lançamentos já está vinculado a outra entrada.')
            if destino == 'RECEBIMENTO':
                linha = conn.execute('SELECT *,valor + COALESCE(multa_juros,0) AS valor_conciliado FROM recebimentos WHERE id=?', (identificador,)).fetchone()
            else:
                linha = conn.execute("SELECT *,valor_total AS valor_conciliado FROM movimentacoes_carteira WHERE id=? AND tipo='CREDITO' AND estornada=0", (identificador,)).fetchone()
            if not linha:
                raise ValueError('Lançamento não encontrado ou já estornado. Atualize a conferência.')
            registros.append(dict(linha))
        if ids and sum(r['valor_conciliado'] for r in registros) != entrada['valor']:
            raise ValueError('A soma dos lançamentos deve ser exatamente igual à entrada bancária.')
        cur = conn.execute('INSERT INTO conciliacoes_bancarias(entrada_id,destino,motivo,vinculos_originais) VALUES(?,?,?,?)',
                           (entrada_id, destino, motivo, json.dumps(registros, ensure_ascii=False)))
        for identificador in ids:
            conn.execute(f'INSERT INTO conciliacoes_vinculos(conciliacao_id,{coluna}) VALUES(?,?)', (cur.lastrowid, identificador))
        return {'sucesso': True, 'id': cur.lastrowid}


def desfazer(identificador, motivo):
    motivo = texto_obrigatorio(motivo, 'o motivo para desfazer')
    with closing(conectar()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        cur = conn.execute("UPDATE conciliacoes_bancarias SET desfeita_em=CURRENT_TIMESTAMP,motivo_desfazer=? WHERE id=? AND desfeita_em IS NULL", (motivo, identificador))
        if not cur.rowcount:
            raise ValueError('Conciliação ativa não encontrada.')
        conn.execute('DELETE FROM conciliacoes_vinculos WHERE conciliacao_id=?', (identificador,))
        return {'sucesso': True, 'id': identificador}

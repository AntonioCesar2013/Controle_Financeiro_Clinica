"""Programação mensal e geração explícita, atômica e repetível de despesas."""
from contextlib import closing
from datetime import date
import sqlite3

from src.infraestrutura.banco import conectar
from src.financeiro.moeda import validar_centavos
from src.financeiro.parcelas import calcular_data_vencimento
from src.financeiro.despesas import validar_para_lancamento


def configurar(despesa_id, valor, data_inicio, data_fim, intervalo_meses=1):
    valor = validar_centavos(valor)
    from src.nucleo.validacao import inteiro
    intervalo_meses = inteiro(intervalo_meses, 'intervalo_meses', 1)
    try:
        inicio, fim = date.fromisoformat(data_inicio), date.fromisoformat(data_fim)
        if inicio.isoformat() != data_inicio or fim.isoformat() != data_fim:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('Informe datas válidas para a recorrência.')
    if valor <= 0 or intervalo_meses > 12 or fim < inicio or (fim-inicio).days > 3660:
        raise ValueError('Informe valor positivo, intervalo de 1 a 12 meses e período de até dez anos.')
    with closing(conectar()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        if not validar_para_lancamento(conn, despesa_id):
            raise ValueError('Selecione uma despesa ativa marcada como recorrente.')
        if conn.execute('SELECT 1 FROM recorrencias_despesas WHERE despesa_id=? AND ativo=1', (despesa_id,)).fetchone():
            raise ValueError('Esta despesa já tem uma programação ativa. Encerre-a antes de configurar outra.')
        cur = conn.execute('INSERT INTO recorrencias_despesas(despesa_id,valor,data_inicio,data_fim,intervalo_meses) VALUES(?,?,?,?,?)',
                           (despesa_id, valor, data_inicio, data_fim, intervalo_meses))
        return {'sucesso': True, 'id': cur.lastrowid}


def gerar(recorrencia_id, data_limite):
    try:
        limite = date.fromisoformat(data_limite)
        if limite.isoformat() != data_limite:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('Informe uma data limite válida.')
    with closing(conectar()) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.execute('BEGIN IMMEDIATE')
        r = conn.execute('''SELECT r.*,d.ativo AS despesa_ativa,s.ativo AS setor_ativo
            FROM recorrencias_despesas r JOIN despesas d ON d.id=r.despesa_id
            JOIN setores s ON s.id=d.setor_id WHERE r.id=?''', (recorrencia_id,)).fetchone()
        if not r or not r['ativo'] or not r['despesa_ativa'] or not r['setor_ativo']:
            raise ValueError('Programação, despesa ou setor inativo ou não encontrado.')
        validar_para_lancamento(conn, r['despesa_id'])
        vencimento = date.fromisoformat(r['data_inicio'])
        fim = min(limite, date.fromisoformat(r['data_fim']))
        numero, criadas, existentes = 0, [], []
        meses_ate_fim = (fim.year-vencimento.year)*12 + fim.month-vencimento.month
        while vencimento <= fim:
            # Também reconhece contas manuais da mesma despesa e vencimento.
            anterior = conn.execute('SELECT id FROM contas_pagar WHERE despesa_id=? AND data_vencimento=?',
                                     (r['despesa_id'], vencimento.isoformat())).fetchone()
            if anterior:
                existentes.append(anterior['id'])
            else:
                cur = conn.execute('''INSERT INTO contas_pagar(despesa_id,data_vencimento,valor,status,recorrencia_id)
                    VALUES(?,?,?,'ABERTA',?)''', (r['despesa_id'], vencimento.isoformat(), r['valor'], r['id']))
                criadas.append(cur.lastrowid)
            numero += r['intervalo_meses']
            if numero > meses_ate_fim:
                break
            vencimento = calcular_data_vencimento(r['data_inicio'], numero)
        return {'sucesso': True, 'id': r['id'], 'quantidade': len(criadas), 'contas_criadas': criadas, 'contas_existentes': existentes}


def encerrar(recorrencia_id):
    with closing(conectar()) as conn, conn:
        cur = conn.execute('UPDATE recorrencias_despesas SET ativo=0 WHERE id=? AND ativo=1', (recorrencia_id,))
        if not cur.rowcount:
            raise ValueError('Programação ativa não encontrada.')
        return {'sucesso': True, 'id': recorrencia_id}


def listar():
    with closing(conectar()) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute('''SELECT r.*,d.descricao FROM recorrencias_despesas r
            JOIN despesas d ON d.id=r.despesa_id ORDER BY r.id DESC''')]

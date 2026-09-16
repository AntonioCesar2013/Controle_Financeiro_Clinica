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
        previa = _prever(conn, r, limite)
        criadas, existentes, conflitos, dispensadas = [], [], [], []
        for item in previa:
            if item['situacao'] == 'A_GERAR':
                cur = conn.execute('''INSERT INTO contas_pagar(despesa_id,data_vencimento,valor,status,recorrencia_id)
                    VALUES(?,?,?,'ABERTA',?)''', (r['despesa_id'], item['data_vencimento'], item['valor_programado'], r['id']))
                criadas.append(cur.lastrowid)
            elif item['situacao'] == 'EXISTENTE':
                existentes.append(item['conta_id'])
            elif item['situacao'] == 'DISPENSADA':
                dispensadas.append(item['data_vencimento'])
            else:
                conflitos.append(item)
        return {'sucesso': True, 'id': r['id'], 'quantidade': len(criadas),
                'contas_criadas': criadas, 'contas_existentes': existentes,
                'conflitos': conflitos, 'competencias_dispensadas': dispensadas}


def _valor_vigente(conn, recorrencia, vencimento):
    ajuste = conn.execute('''SELECT valor FROM recorrencias_reajustes
        WHERE recorrencia_id=? AND data_inicio_vigencia<=?
        ORDER BY data_inicio_vigencia DESC,id DESC LIMIT 1''',
        (recorrencia['id'], vencimento)).fetchone()
    return ajuste[0] if ajuste else recorrencia['valor']


def _prever(conn, recorrencia, limite):
    vencimento = date.fromisoformat(recorrencia['data_inicio'])
    fim = min(limite, date.fromisoformat(recorrencia['data_fim']))
    numero, itens = 0, []
    meses_ate_fim = (fim.year-vencimento.year)*12 + fim.month-vencimento.month
    while vencimento <= fim:
        data_vencimento = vencimento.isoformat()
        valor = _valor_vigente(conn, recorrencia, data_vencimento)
        dispensada = conn.execute('''SELECT motivo FROM recorrencias_competencias_dispensadas
            WHERE recorrencia_id=? AND data_vencimento=?''',
            (recorrencia['id'], data_vencimento)).fetchone()
        contas = conn.execute('''SELECT id,valor,status,recorrencia_id FROM contas_pagar
            WHERE despesa_id=? AND data_vencimento=? ORDER BY id''',
            (recorrencia['despesa_id'], data_vencimento)).fetchall()
        efetivas = [conta for conta in contas if conta['status'] != 'CANCELADA']
        conta = efetivas[0] if efetivas else (contas[0] if contas else None)
        if dispensada and not efetivas:
            situacao = 'DISPENSADA'
        elif dispensada and efetivas:
            situacao = 'CONFLITO_DISPENSA'
        elif not conta:
            situacao = 'A_GERAR'
        elif len(efetivas) > 1:
            situacao = 'CONFLITO_MULTIPLAS_CONTAS'
        elif conta['status'] == 'CANCELADA':
            situacao = 'CONTA_CANCELADA'
        elif conta['valor'] != valor:
            situacao = 'CONFLITO_VALOR'
        else:
            situacao = 'EXISTENTE'
        itens.append({'data_vencimento': data_vencimento, 'valor_programado': valor,
                      'situacao': situacao, 'conta_id': conta['id'] if conta else None,
                      'valor_conta': conta['valor'] if conta else None,
                      'motivo_dispensa': dispensada[0] if dispensada else None})
        numero += recorrencia['intervalo_meses']
        if numero > meses_ate_fim:
            break
        vencimento = calcular_data_vencimento(recorrencia['data_inicio'], numero)
    return itens


def previa(recorrencia_id, data_limite):
    try:
        limite = date.fromisoformat(data_limite)
    except (TypeError, ValueError):
        raise ValueError('Informe uma data limite válida.')
    with closing(conectar()) as conn:
        conn.row_factory = sqlite3.Row
        r = conn.execute('SELECT * FROM recorrencias_despesas WHERE id=?', (recorrencia_id,)).fetchone()
        if not r:
            raise ValueError('Programação não encontrada.')
        return {'id': r['id'], 'itens': _prever(conn, r, limite)}


def reajustar(recorrencia_id, valor, data_inicio_vigencia, motivo):
    valor = validar_centavos(valor)
    motivo = str(motivo or '').strip()
    try:
        vigencia = date.fromisoformat(data_inicio_vigencia)
    except (TypeError, ValueError):
        raise ValueError('Informe uma vigência válida para o reajuste.')
    if valor <= 0 or not motivo:
        raise ValueError('Informe valor positivo e motivo do reajuste.')
    with closing(conectar()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        r = conn.execute('SELECT data_inicio,data_fim FROM recorrencias_despesas WHERE id=? AND ativo=1',
                         (recorrencia_id,)).fetchone()
        if not r or not r[0] <= vigencia.isoformat() <= r[1]:
            raise ValueError('Programação ativa não encontrada ou vigência fora do período.')
        cur = conn.execute('''INSERT INTO recorrencias_reajustes
            (recorrencia_id,valor,data_inicio_vigencia,motivo) VALUES(?,?,?,?)''',
            (recorrencia_id, valor, vigencia.isoformat(), motivo))
        return {'sucesso': True, 'id': cur.lastrowid}


def dispensar_competencia(recorrencia_id, data_vencimento, motivo):
    motivo = str(motivo or '').strip()
    if not motivo:
        raise ValueError('Informe o motivo da dispensa desta competência.')
    with closing(conectar()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        recorrencia = conn.execute('SELECT despesa_id FROM recorrencias_despesas WHERE id=?',
                                  (recorrencia_id,)).fetchone()
        if not recorrencia:
            raise ValueError('Programação não encontrada.')
        if conn.execute('''SELECT 1 FROM contas_pagar WHERE despesa_id=? AND data_vencimento=?
                           AND status!='CANCELADA' LIMIT 1''',
                        (recorrencia[0], data_vencimento)).fetchone():
            raise ValueError('A competência já possui conta efetiva; cancele ou trate a conta antes da dispensa.')
        conn.execute('''INSERT INTO recorrencias_competencias_dispensadas
            (recorrencia_id,data_vencimento,motivo) VALUES(?,?,?)''',
            (recorrencia_id, data_vencimento, motivo))
        return {'sucesso': True, 'id': recorrencia_id, 'data_vencimento': data_vencimento}


def encerrar(recorrencia_id):
    with closing(conectar()) as conn, conn:
        cur = conn.execute('UPDATE recorrencias_despesas SET ativo=0 WHERE id=? AND ativo=1', (recorrencia_id,))
        if not cur.rowcount:
            raise ValueError('Programação ativa não encontrada.')
        return {'sucesso': True, 'id': recorrencia_id}


def listar():
    with closing(conectar()) as conn:
        conn.row_factory = sqlite3.Row
        registros = [dict(r) for r in conn.execute('''SELECT r.*,d.descricao FROM recorrencias_despesas r
            JOIN despesas d ON d.id=r.despesa_id ORDER BY r.id DESC''')]
        for r in registros:
            itens = _prever(conn, r, date.fromisoformat(r['data_fim']))
            pendentes = [i for i in itens if i['situacao'] == 'A_GERAR']
            r['proxima_geracao'] = pendentes[0]['data_vencimento'] if pendentes else None
            r['periodos_nao_gerados'] = len(pendentes)
            r['conflitos'] = sum(i['situacao'].startswith('CONFLITO') or i['situacao']=='CONTA_CANCELADA' for i in itens)
        return registros

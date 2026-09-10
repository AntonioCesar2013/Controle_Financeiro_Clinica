"""Conferência de posições atuais e fechamento versionado de movimentos mensais.

Um fechamento conserva sua fotografia original. Mudanças retroativas tornam
a revisão divergente; uma nova versão exige reabertura justificada.
"""
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import date

from src.infraestrutura.banco import conectar
from src.cantina.api_publica import dados_conferencia
from src.financeiro import caixa, conciliacao
from src.financeiro.moeda import validar_centavos


def serializar(dados):
    return json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def assinatura(dados):
    return hashlib.sha256(serializar(dados).encode('utf-8')).hexdigest()


def _abrir():
    conn = conectar()
    conn.row_factory = sqlite3.Row
    return conn


def _posicao(conn):
    receber = [dict(r) for r in conn.execute('''
        SELECT c.id,r.nome || ' — parcela ' || c.numero_parcela AS nome,
               c.valor-c.desconto-COALESCE((SELECT SUM(valor) FROM recebimentos WHERE cobranca_id=c.id),0) AS valor
        FROM cobrancas c JOIN internacoes i ON i.id=c.internacao_id
        JOIN residentes r ON r.id=i.residente_id WHERE c.status!='CANCELADA' ORDER BY c.id''')]
    pagar = [dict(r) for r in conn.execute('''
        SELECT c.id,d.descricao AS nome,
               c.valor-c.desconto-COALESCE((SELECT SUM(valor) FROM pagamentos_saida WHERE conta_pagar_id=c.id),0) AS valor
        FROM contas_pagar c JOIN despesas d ON d.id=c.despesa_id
        WHERE c.status!='CANCELADA' ORDER BY c.id''')]
    cantina = dados_conferencia(conn)
    itens = []
    for tipo, registros, campo in (
        ('RECEBER', [r for r in receber if r['valor']], 'valor'),
        ('PAGAR', [r for r in pagar if r['valor']], 'valor'),
        ('CARTEIRA', cantina['carteiras'], 'saldo'),
        ('ESTOQUE', cantina['estoque'], 'estoque_atual'),
    ):
        for r in registros:
            itens.append({'chave': f"{tipo}:{r['id']}", 'tipo': tipo, 'nome': r['nome'],
                          'valor': r[campo], 'unidade': r.get('unidade_medida', 'R$')})
    return {'data': date.today().isoformat(), 'itens': itens,
            'totais': {tipo: sum(r['valor'] for r in itens if r['tipo']==tipo)
                       for tipo in ('RECEBER','PAGAR','CARTEIRA')}}


def saldos():
    with closing(_abrir()) as conn:
        conn.execute('BEGIN')
        dados = _posicao(conn)
        historico = [dict(r) for r in conn.execute('SELECT * FROM conferencias_saldos ORDER BY id DESC')]
        for r in historico:
            r['dados'] = json.loads(r['dados'])
        return {**dados, 'assinatura': assinatura(dados), 'historico': historico}


def conferir_saldos(hash_esperado, valores, responsavel, observacao):
    responsavel = conciliacao.texto_obrigatorio(responsavel, 'quem fez a conferência')
    observacao = conciliacao.texto_obrigatorio(observacao, 'os documentos usados na conferência')
    if not isinstance(valores, dict):
        raise ValueError('Informe os valores conferidos de todos os itens.')
    with closing(_abrir()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        dados = _posicao(conn)
        if assinatura(dados) != hash_esperado:
            raise ValueError('Os saldos mudaram. Atualize a tela e confira novamente.')
        if set(valores) != {r['chave'] for r in dados['itens']}:
            raise ValueError('Confira todos os itens da posição atual.')
        divergentes = 0
        for item in dados['itens']:
            valor = validar_centavos(valores[item['chave']])
            if item['tipo'] != 'CARTEIRA' and valor < 0:
                raise ValueError('Somente carteiras podem ter saldo conferido negativo.')
            item['conferido'] = valor
            item['diferenca'] = valor - item['valor']
            divergentes += item['diferenca'] != 0
        status = 'DIVERGENTE' if divergentes else 'CONFERIDA'
        cur = conn.execute('INSERT INTO conferencias_saldos(responsavel,observacao,status,dados) VALUES(?,?,?,?)',
                           (responsavel, observacao, status, serializar(dados)))
        return {'sucesso': True, 'id': cur.lastrowid, 'status': status, 'divergencias': divergentes}


def _periodo(competencia):
    if not isinstance(competencia, str) or not re.fullmatch(r'\d{4}-\d{2}', competencia):
        raise ValueError('Informe o mês no formato AAAA-MM.')
    inicio, fim = caixa._periodo_mensal(*competencia.split('-'))
    return inicio.isoformat(), fim.isoformat()


def _mes(conn, competencia):
    inicio, fim = _periodo(competencia)
    movimentos = caixa.listar_movimentacoes(inicio, fim, conexao=conn)
    cantina = dados_conferencia(conn, inicio, fim)
    entradas = [r for r in conciliacao.listar(conn) if inicio <= r['data_entrada'] <= fim]
    return {
        'competencia': competencia, 'inicio': inicio, 'fim': fim,
        'clinica': {'entradas': sum(r['valor'] for r in movimentos if r['tipo']=='ENTRADA'),
                    'saidas': sum(r['valor'] for r in movimentos if r['tipo']=='SAIDA'),
                    'movimentos': movimentos},
        'carteiras': {k: cantina[k] for k in ('saldo_abertura','saldo_fechamento','creditos','compras','movimentos')},
        'banco': entradas, 'pendentes': sum(r['destino']=='PENDENTE' for r in entradas),
    }


def mensal(competencia):
    with closing(_abrir()) as conn:
        conn.execute('BEGIN')
        dados = _mes(conn, competencia)
        atual = assinatura(dados)
        historico = [dict(r) for r in conn.execute('SELECT * FROM fechamentos_mensais WHERE competencia=? ORDER BY revisao DESC', (competencia,))]
        for r in historico:
            r['dados'] = json.loads(r['dados'])
            r['status'] = 'REABERTO' if r['reaberto_em'] else ('FECHADO' if r['assinatura']==atual else 'REVISAR')
        return {**dados, 'assinatura': atual, 'historico': historico}


def fechar(competencia, hash_esperado, responsavel, observacao, valores):
    responsavel = conciliacao.texto_obrigatorio(responsavel, 'quem conferiu o mês')
    observacao = conciliacao.texto_obrigatorio(observacao, 'os documentos e observações do fechamento')
    with closing(_abrir()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        dados = _mes(conn, competencia)
        if dados['fim'] >= date.today().isoformat():
            raise ValueError('O mês precisa estar encerrado para registrar o fechamento.')
        if assinatura(dados) != hash_esperado:
            raise ValueError('Os movimentos mudaram. Atualize e confira novamente.')
        if dados['pendentes']:
            raise ValueError('Concilie ou classifique todas as entradas bancárias do mês antes de fechar.')
        esperados = {'entradas': dados['clinica']['entradas'], 'saidas': dados['clinica']['saidas'],
                     'creditos': dados['carteiras']['creditos'], 'compras': dados['carteiras']['compras'],
                     'saldo_carteiras': dados['carteiras']['saldo_fechamento']}
        if not isinstance(valores, dict) or set(valores) != set(esperados):
            raise ValueError('Informe os cinco totais conferidos nos documentos.')
        if any(validar_centavos(valores[k]) != v for k,v in esperados.items()):
            raise ValueError('Os totais conferidos divergem do sistema. Acerte os lançamentos antes de fechar.')
        if conn.execute('SELECT 1 FROM fechamentos_mensais WHERE competencia=? AND reaberto_em IS NULL', (competencia,)).fetchone():
            raise ValueError('O mês já possui fechamento. Reabra com motivo antes de registrar outra revisão.')
        revisao = conn.execute('SELECT COALESCE(MAX(revisao),0)+1 FROM fechamentos_mensais WHERE competencia=?', (competencia,)).fetchone()[0]
        cur = conn.execute('INSERT INTO fechamentos_mensais(competencia,revisao,responsavel,observacao,dados,assinatura) VALUES(?,?,?,?,?,?)',
                           (competencia, revisao, responsavel, observacao, serializar(dados), assinatura(dados)))
        return {'sucesso': True, 'id': cur.lastrowid, 'revisao': revisao}


def reabrir(identificador, motivo):
    motivo = conciliacao.texto_obrigatorio(motivo, 'o motivo da reabertura')
    with closing(_abrir()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        cur = conn.execute('UPDATE fechamentos_mensais SET reaberto_em=CURRENT_TIMESTAMP,motivo_reabertura=? WHERE id=? AND reaberto_em IS NULL', (motivo, identificador))
        if not cur.rowcount:
            raise ValueError('Fechamento ativo não encontrado.')
        return {'sucesso': True, 'id': identificador}

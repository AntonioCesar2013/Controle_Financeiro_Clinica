"""Prévia e registro do acerto contratual, sem presumir dispensa de dívida."""
from contextlib import closing
from datetime import date, timedelta
import json
import sqlite3
import hashlib

from src.infraestrutura.banco import conectar
from src.financeiro.parcelas import calcular_data_vencimento


def previa(internacao_id, data_encerramento, politica=None, conexao=None):
    if conexao is None:
        with closing(conectar()) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute('BEGIN')
            return previa(internacao_id, data_encerramento, politica, conn)
    conn = conexao
    conn.row_factory = sqlite3.Row
    try:
        fim = date.fromisoformat(data_encerramento)
        if fim.isoformat() != data_encerramento or fim > date.today():
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('Data de encerramento inválida ou futura.')
    i = conn.execute('SELECT * FROM internacoes WHERE id=?', (internacao_id,)).fetchone()
    if not i or i['status'] == 'CANCELADA' or i['encerrada_em']:
        raise ValueError('Internação não encontrada, cancelada ou já encerrada antecipadamente.')
    if data_encerramento < i['data_acolhimento']:
        raise ValueError('O encerramento não pode anteceder o acolhimento.')
    if i['modalidade'] != 'VOLUNTARIO' and fim > calcular_data_vencimento(i['data_acolhimento'], i['periodo_tratamento']):
        raise ValueError('O encerramento não pode ultrapassar o período contratado.')
    if i['modalidade'] == 'PARTICULAR':
        if politica not in ('MANTER', 'DISPENSAR_FUTURAS'):
            raise ValueError('Escolha manter as cobranças ou dispensar mensalidades com vencimento após a saída.')
    else:
        politica = 'DIARIAS' if i['modalidade'] == 'CONVENIO' else 'SEM_COBRANCAS'
    linhas = []
    # A competência original pode conter parcelas de prorrogação; as diárias
    # são calculadas pelo intervalo real de cada parcela, sem renumerá-las.
    inicio_diarias = date.fromisoformat(i['data_acolhimento'])
    for c in conn.execute('''SELECT c.*,COALESCE((SELECT SUM(valor) FROM recebimentos_liquidos
        WHERE cobranca_id=c.id),0) AS recebido FROM cobrancas c
        WHERE internacao_id=? ORDER BY numero_parcela''', (internacao_id,)):
        valor = c['valor']
        if politica == 'DISPENSAR_FUTURAS' and c['tipo'] == 'MENSALIDADE' and c['data_vencimento'] > data_encerramento:
            valor = 0
        if politica == 'DIARIAS':
            fim_parcela = date.fromisoformat(c['data_vencimento'])
            valor = max(0, (min(fim, fim_parcela)-inicio_diarias).days+1) * i['valor_diaria']
            inicio_diarias = fim_parcela + timedelta(days=1)
        desconto = min(c['desconto'], max(0, valor-c['recebido']))
        linhas.append({'id': c['id'], 'numero_parcela': c['numero_parcela'],
                       'valor_anterior': c['valor'], 'valor_novo': valor,
                       'desconto_anterior': c['desconto'], 'desconto_novo': desconto,
                       'recebido': c['recebido'], 'devolver': max(0, c['recebido']-valor),
                       'saldo_restante': max(0, valor-desconto-c['recebido'])})
    carteira = conn.execute('SELECT id,saldo FROM carteiras WHERE residente_id=?', (i['residente_id'],)).fetchone()
    dados = {'internacao_id': i['id'], 'modalidade': i['modalidade'], 'politica': politica,
            'data_encerramento': data_encerramento, 'cobrancas': linhas,
            'total_devolver': sum(c['devolver'] for c in linhas),
            'total_pendente': sum(c['saldo_restante'] for c in linhas),
            'carteira': dict(carteira) if carteira else None}
    dados['assinatura'] = hashlib.sha256(json.dumps(dados, sort_keys=True).encode()).hexdigest()
    return dados


def aplicar(internacao_id, data_encerramento, conn, politica, motivo, autorizar_ajuste_desconto=False, assinatura=None):
    dados = previa(internacao_id, data_encerramento, politica, conn)
    if assinatura is not None and assinatura != dados['assinatura']:
        raise ValueError('O acerto mudou. Consulte e confira novamente a prévia antes de encerrar.')
    if dados['total_devolver']:
        raise ValueError(f"Registre a devolução de R$ {dados['total_devolver']/100:.2f} dos recebimentos indicados na prévia antes de encerrar.")
    for c in dados['cobrancas']:
        if c['desconto_novo'] != c['desconto_anterior'] and not autorizar_ajuste_desconto:
            raise ValueError('Confirme o ajuste de descontos indicado na prévia antes de encerrar.')
        if (c['valor_novo'], c['desconto_novo']) != (c['valor_anterior'], c['desconto_anterior']):
            conn.execute('''INSERT INTO ajustes_cobrancas(cobranca_id,valor_anterior,valor_novo,
                desconto_anterior,desconto_novo,motivo) VALUES(?,?,?,?,?,?)''',
                (c['id'], c['valor_anterior'], c['valor_novo'], c['desconto_anterior'], c['desconto_novo'], motivo))
        devido = c['valor_novo']-c['desconto_novo']
        status = 'DESCONTADA' if devido == 0 else 'PAGA' if devido == c['recebido'] else 'PARCIAL' if c['recebido'] else 'ABERTA'
        conn.execute('UPDATE cobrancas SET valor=?,desconto=?,status=? WHERE id=?',
                     (c['valor_novo'], c['desconto_novo'], status, c['id']))
    conn.execute('UPDATE internacoes SET valor_contrato=(SELECT COALESCE(SUM(valor),0) FROM cobrancas WHERE internacao_id=?) WHERE id=?', (internacao_id, internacao_id))
    conn.execute('INSERT INTO acertos_encerramento(internacao_id,data_encerramento,politica,motivo,dados) VALUES(?,?,?,?,?)',
                 (internacao_id, data_encerramento, dados['politica'], motivo, json.dumps(dados, ensure_ascii=False)))
    return dados

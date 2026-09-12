"""Acrescenta cobranças preservando as parcelas e recebimentos existentes."""
from datetime import timedelta
from src.financeiro.parcelas import calcular_data_vencimento
from src.financeiro.cobrancas import _competencias_diarias


def acrescentar(conn, internacao, novo_periodo):
    i = internacao
    anterior = i['periodo_tratamento']
    novas = []
    if i['modalidade'] == 'PARTICULAR':
        novas = [(n, calcular_data_vencimento(i['data_acolhimento'], n), i['valor_mensalidade'])
                 for n in range(anterior+1, novo_periodo+1)]
    elif i['modalidade'] == 'CONVENIO':
        inicio = calcular_data_vencimento(i['data_acolhimento'], anterior) + timedelta(days=1)
        fim = calcular_data_vencimento(i['data_acolhimento'], novo_periodo)
        ultima = conn.execute('SELECT COALESCE(MAX(numero_parcela),0) FROM cobrancas WHERE internacao_id=?', (i['id'],)).fetchone()[0]
        novas = [(ultima+n, vencimento, valor) for n, vencimento, valor in _competencias_diarias(inicio, fim, i['valor_diaria'])]
    for numero, vencimento, valor in novas:
        conn.execute('''INSERT INTO cobrancas(internacao_id,numero_parcela,tipo,data_vencimento,valor,desconto,status)
            VALUES(?,?,'MENSALIDADE',?,?,0,?)''', (i['id'], numero, vencimento.isoformat(), valor, 'ABERTA' if valor else 'DESCONTADA'))
    return len(novas), sum(n[2] for n in novas)

"""Operações públicas da Cantina para consumidores externos."""

from src.cantina.vendas import consultar_carteira
from src.cantina.vendas import _eh_servico


def obter_saldo_residente(carteira_id):
    """Retorna os dados da carteira; o saldo pode ser negativo por regra."""
    return consultar_carteira(carteira_id)


def dados_conferencia(conexao, inicio=None, fim=None):
    """Posições atuais e movimentos efetivos; nunca entram como receita clínica."""
    carteiras = [dict(r) for r in conexao.execute('''
        SELECT c.id,r.nome,c.saldo,c.ativo FROM carteiras c
        JOIN residentes r ON r.id=c.residente_id ORDER BY c.id''')]
    estoque = [dict(r) for r in conexao.execute('''
        SELECT id,nome,unidade_medida,estoque_atual,categoria FROM itens ORDER BY id''')
        if not _eh_servico(r['categoria'])]
    todos = [dict(r) for r in conexao.execute('''
        SELECT id,carteira_id,tipo,valor_total,data_movimentacao,estornada
        FROM movimentacoes_carteira ORDER BY data_movimentacao,id''')]
    def efeito(m):
        if m['estornada']:
            return 0
        return m['valor_total'] if m['tipo'] == 'CREDITO' else -abs(m['valor_total'])
    movimentos = [m for m in todos if (not inicio or m['data_movimentacao'] >= inicio)
                  and (not fim or m['data_movimentacao'] <= fim)]
    abertura = fechamento = 0
    for c in carteiras:
        historico = [m for m in todos if m['carteira_id'] == c['id']]
        residual = c['saldo'] - sum(efeito(m) for m in historico)
        abertura += residual + sum(efeito(m) for m in historico if inicio and m['data_movimentacao'] < inicio)
        fechamento += residual + sum(efeito(m) for m in historico if not fim or m['data_movimentacao'] <= fim)
    return {'carteiras': carteiras, 'estoque': estoque, 'movimentos': movimentos,
            'saldo_abertura': abertura, 'saldo_fechamento': fechamento,
            'creditos': sum(m['valor_total'] for m in movimentos if not m['estornada'] and m['tipo']=='CREDITO'),
            'compras': sum(abs(m['valor_total']) for m in movimentos if not m['estornada'] and m['tipo']!='CREDITO')}

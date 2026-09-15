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
        SELECT id,nome,unidade_medida,estoque_atual,categoria FROM itens_cantina ORDER BY id''')
        if not _eh_servico(r['categoria'])]
    movimentos = [dict(r) for r in conexao.execute('''
        SELECT id,carteira_id,tipo,valor_total,data_movimentacao,estornada
        FROM movimentacoes_carteira
        WHERE (? IS NULL OR data_movimentacao>=?) AND (? IS NULL OR data_movimentacao<=?)
        ORDER BY data_movimentacao,id''', (inicio, inicio, fim, fim))]
    agregados = conexao.execute('''
        WITH efeitos AS (
            SELECT carteira_id, data_movimentacao,
                   CASE WHEN estornada=1 THEN 0
                        WHEN tipo='CREDITO' THEN valor_total
                        ELSE -ABS(valor_total) END AS efeito
            FROM movimentacoes_carteira
        ), por_carteira AS (
            SELECT c.id, c.saldo,
                   COALESCE(SUM(e.efeito), 0) AS historico,
                   COALESCE(SUM(CASE WHEN ? IS NOT NULL AND e.data_movimentacao<? THEN e.efeito ELSE 0 END), 0) AS antes,
                   COALESCE(SUM(CASE WHEN ? IS NULL OR e.data_movimentacao<=? THEN e.efeito ELSE 0 END), 0) AS ate_fim
            FROM carteiras c LEFT JOIN efeitos e ON e.carteira_id=c.id
            GROUP BY c.id
        )
        SELECT COALESCE(SUM(saldo-historico+antes), 0),
               COALESCE(SUM(saldo-historico+ate_fim), 0)
        FROM por_carteira
    ''', (inicio, inicio, fim, fim)).fetchone()
    abertura, fechamento = agregados
    return {'carteiras': carteiras, 'estoque': estoque, 'movimentos': movimentos,
            'saldo_abertura': abertura, 'saldo_fechamento': fechamento,
            'creditos': sum(m['valor_total'] for m in movimentos if not m['estornada'] and m['tipo']=='CREDITO'),
            'devolucoes': sum(m['valor_total'] for m in movimentos if not m['estornada'] and m['tipo']=='DEVOLUCAO'),
            'compras': sum(abs(m['valor_total']) for m in movimentos if not m['estornada'] and m['tipo'] not in ('CREDITO','DEVOLUCAO'))}

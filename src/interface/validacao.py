"""Validação estrutural da API; regras financeiras permanecem no domínio."""
import re
from datetime import date
from src.financeiro.moeda import reais_para_centavos


OBRIGATORIOS = {
    '/api/residentes': ('nome','cpf'), '/api/residentes/editar': ('id','nome','cpf'),
    '/api/responsaveis': ('nome','cpf'), '/api/responsaveis/editar': ('id','nome','cpf'),
    '/api/internacoes': ('residente_id','responsavel_id','data_acolhimento','periodo_tratamento'),
    '/api/internacoes/cancelar': ('id','motivo'), '/api/internacoes/encerrar': ('id','data_encerramento','motivo'),
    '/api/internacoes/responsavel': ('id','responsavel_id'),
    '/api/convenios': ('nome','valor_diaria'), '/api/colaboradores': ('nome','cpf','senha'),
    '/api/colaboradores/editar': ('id','nome','cpf','status'), '/api/colaboradores/senha': ('id','senha'),
    '/api/itens': ('nome','valor'), '/api/itens/editar': ('id','nome'),
    '/api/itens/precos': ('item_id','valor','data_inicio_valor'),
    '/api/itens/estoque': ('item_id','quantidade','motivo'),
    '/api/carteiras': ('residente_id',), '/api/carteiras/credito': ('carteira_id','valor'),
    '/api/carteiras/status': ('carteira_id','ativo'),
    '/api/carteiras/movimentacoes/estornar': ('movimentacao_id','motivo'),
    '/api/carteiras/movimentacoes/corrigir': ('movimentacao_id','valor','motivo'),
    '/api/cantina/vendas': ('carteira_id','item_id'), '/api/cantina/checkout': ('carteira_id','produtos'),
    '/api/cantina/vendas/estornar': ('venda_id','motivo'),
    '/api/setores': ('nome',), '/api/setores/editar': ('id','nome','ativo'),
    '/api/despesas': ('setor_id','descricao'), '/api/despesas/desativar': ('id',),
    '/api/contas-pagar': ('despesa_id','data_vencimento','valor'),
    '/api/contas-pagar/cancelar': ('conta_id',),
    '/api/pagamentos-saida': ('conta_pagar_id','data_pagamento','valor'),
    '/api/recebimentos': ('cobranca_id','data_pagamento','valor'),
    '/api/pagamentos-saida/excluir': ('pagamento_id','motivo'),
    '/api/recebimentos/excluir': ('recebimento_id','motivo'),
    '/api/cobrancas/desconto': ('cobranca_id','valor'), '/api/recibos': ('recebimento_id',),
    '/api/conciliacao/vincular': ('entrada_id','destino','ids','motivo'),
    '/api/conciliacao/desfazer': ('id','motivo'),
    '/api/conferencia/saldos': ('assinatura','valores','responsavel','observacao'),
    '/api/conferencia/fechar': ('competencia','assinatura','valores','responsavel','observacao'),
    '/api/conferencia/reabrir': ('id','motivo'),
}
MONETARIOS = {'valor','desconto','saldo_inicial','custo_unitario','valor_diaria',
              'valor_contrato','valor_acolhimento','valor_mensalidade'}
INTEIROS = {'quantidade','estoque_inicial','estoque_minimo','periodo_tratamento'}
BOOLEANOS = {'ativo','recorrente','autorizar_ajuste_desconto'}


def inteiro(valor, nome, minimo=None):
    if isinstance(valor, bool) or not isinstance(valor, (str,int)) or not re.fullmatch(r'-?\d+', str(valor)):
        raise ValueError(f'O campo {nome} deve ser um número inteiro.')
    numero = int(valor)
    if abs(numero) > 2_000_000_000 or (minimo is not None and numero < minimo):
        raise ValueError(f'O campo {nome} está fora do intervalo permitido.')
    return numero


def validar(rota, dados):
    if rota not in OBRIGATORIOS:
        raise LookupError('Rota não encontrada.')
    if not isinstance(dados, dict):
        raise ValueError('O corpo da requisição deve ser um objeto JSON.')
    for campo in OBRIGATORIOS[rota]:
        if campo not in dados or dados[campo] is None or (isinstance(dados[campo],str) and not dados[campo].strip()):
            raise ValueError(f'Preencha o campo obrigatório: {campo}.')
    for campo, valor in dados.items():
        if len(campo) > 100:
            raise ValueError('Nome de campo inválido.')
        if campo == 'produtos':
            if not isinstance(valor,list) or not 1 <= len(valor) <= 500:
                raise ValueError('O carrinho deve conter de 1 a 500 itens.')
            for item in valor:
                if not isinstance(item,dict):
                    raise ValueError('Cada item do carrinho deve ser um objeto.')
                inteiro(item.get('item_id'), 'item_id', 1)
                inteiro(item.get('quantidade',1), 'quantidade', 1)
            continue
        if campo == 'ids':
            if not isinstance(valor,list) or len(valor)>1000 or any(type(i) is not int or i <= 0 for i in valor):
                raise ValueError('A lista de vínculos deve conter identificadores inteiros positivos.')
            continue
        if campo == 'valores':
            if not isinstance(valor,dict) or len(valor)>10000:
                raise ValueError('Os valores da conferência devem ser um objeto válido.')
            for chave, numero in valor.items():
                if len(chave)>100 or isinstance(numero,bool) or not isinstance(numero,(str,int,float)) or str(numero).strip()=='':
                    raise ValueError('Preencha os valores da conferência corretamente.')
                reais_para_centavos(numero)
            continue
        if isinstance(valor, (dict,list)):
            raise ValueError(f'O campo {campo} não aceita listas ou objetos.')
        if valor is None or valor == '':
            continue
        if campo.endswith('_id') or campo == 'id':
            inteiro(valor,campo,1)
        elif campo in INTEIROS:
            inteiro(valor,campo, None if campo=='quantidade' and rota=='/api/itens/estoque' else 0)
        elif campo in MONETARIOS:
            reais_para_centavos(valor)
        elif campo in BOOLEANOS:
            if str(valor).lower() not in ('0','1','true','false'):
                raise ValueError(f'O campo {campo} deve indicar sim ou não.')
        elif campo.startswith('data_'):
            try:
                if not isinstance(valor,str) or date.fromisoformat(valor).isoformat()!=valor:
                    raise ValueError
            except (TypeError,ValueError):
                raise ValueError(f'O campo {campo} deve conter uma data válida no formato AAAA-MM-DD.')
        elif not isinstance(valor,str) or len(valor)>10000:
            raise ValueError(f'O campo {campo} deve ser um texto de até 10000 caracteres.')

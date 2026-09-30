"""Normaliza textos de negócio sem modificar identificadores técnicos ou segredos."""

CAMPOS_TEXTO = frozenset({
    'nome', 'descricao', 'observacao', 'observacoes', 'motivo', 'documento',
    'fornecedor', 'lote', 'unidade_medida', 'servicos_voluntario', 'responsavel',
    'categoria', 'codigo_patrimonio', 'localizacao', 'localizacao_destino',
    'relacao', 'endereco', 'bairro', 'cidade', 'estado', 'complemento',
})


def normalizar_textos(dados):
    return {campo: valor.upper() if campo in CAMPOS_TEXTO and isinstance(valor, str) else valor
            for campo, valor in dados.items()}

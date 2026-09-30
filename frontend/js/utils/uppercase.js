const TEXT_FIELDS = new Set(['nome', 'descricao', 'observacao', 'observacoes', 'motivo',
    'documento', 'fornecedor', 'lote', 'unidade_medida', 'servicos_voluntario',
    'responsavel', 'categoria', 'codigo_patrimonio', 'localizacao', 'localizacao_destino',
    'relacao', 'endereco', 'bairro', 'cidade', 'estado', 'complemento']);

export function uppercaseInput(input) {
    if (!input?.matches?.('input, textarea') || input.readOnly || input.disabled) return;
    if (input.matches('[data-backup-config], [data-backup-secret], [data-preserve-case], [data-mask]')) return;
    if (input.tagName !== 'TEXTAREA' && !['text', 'search'].includes(input.type)) return;
    if (input.name && !TEXT_FIELDS.has(input.name) && input.type !== 'search') return;
    const value = input.value;
    const upper = value.toLocaleUpperCase('pt-BR');
    if (value === upper) return;
    const start = input.selectionStart, end = input.selectionEnd, direction = input.selectionDirection;
    input.value = upper;
    if (start !== null && end !== null) input.setSelectionRange(
        value.slice(0, start).toLocaleUpperCase('pt-BR').length,
        value.slice(0, end).toLocaleUpperCase('pt-BR').length, direction);
}

export function installUppercase(root) {
    const normalize = event => { if (!event.isComposing) uppercaseInput(event.target); };
    root.addEventListener('input', normalize, true);
    root.addEventListener('change', normalize, true);
    root.addEventListener('compositionend', normalize, true);
    root.addEventListener('submit', event => {
        event.target.querySelectorAll('input, textarea').forEach(uppercaseInput);
    }, true);
}

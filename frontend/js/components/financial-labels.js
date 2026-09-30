import { localDate } from '../utils/formatters.js';

export function shortSector(value) {
    return String(value || '').trim().toLocaleUpperCase('pt-BR').slice(0, 3) || '—';
}

export function shortInitial(value) {
    return String(value || '').trim().toLocaleUpperCase('pt-BR').slice(0, 1) || '—';
}

export function receivableType(value, row = {}) {
    if (row.setor_nome) return shortSector(row.setor_nome);
    const type = String(value || '').trim().toLocaleUpperCase('pt-BR');
    return ['MENSALIDADE', 'ACOLHIMENTO'].includes(type) ? `${type.slice(0, 3)}...` : shortSector(type);
}

export function receivablePayment(value, row, today = localDate()) {
    if (Number(row.saldo_restante) > 0 && !['PAGA', 'DESCONTADA', 'CANCELADA'].includes(value)
        && row.data_vencimento && row.data_vencimento < today) return 'ATRASO';
    return value || '—';
}

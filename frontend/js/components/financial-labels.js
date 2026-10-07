import { localDate } from '../utils/formatters.js';

export function shortSector(value) {
    return String(value || '').trim().toLocaleUpperCase('pt-BR').slice(0, 3) || '—';
}

export function shortInitial(value) {
    return String(value || '').trim().toLocaleUpperCase('pt-BR').slice(0, 1) || '—';
}

export function receivableType(value, row = {}) {
    const type = String(value || '').trim().toLocaleUpperCase('pt-BR');
    if (type === 'MENSALIDADE') return 'M';
    if (type === 'ACOLHIMENTO') return 'A';
    return 'O';
}

export function receivablePayment(value, row, today = localDate()) {
    if (Number(row.saldo_restante) > 0 && !['PAGA', 'DESCONTADA', 'CANCELADA'].includes(value)
        && row.data_vencimento && row.data_vencimento < today) return 'ATRASO';
    return value || '—';
}

import assert from 'node:assert/strict';
import { createWorkflows } from '../frontend/js/components/workflows.js';

let body = '';
const workflows = createWorkflows({
    api: async path => path === '/api/responsaveis'
        ? { dados: [{id: 2, nome: 'Responsável', ativo: 1}] }
        : path.startsWith('/api/internacoes/acerto')
        ? { dados: { assinatura: 'assinatura-conferida', cobrancas: [{numero_parcela: 1, valor_anterior: 10000, valor_novo: 0, desconto_anterior: 0, desconto_novo: 0, recebido: 10000, devolver: 10000, saldo_restante: 0}], total_devolver: 10000, total_pendente: 0, carteira: { saldo: -500 } } }
        : { dados: [{id: 1, modalidade: 'PARTICULAR', periodo_tratamento: 2}] },
    showPanel: (_, html) => { body = html; },
    showAlert: (_, message) => { throw new Error(message); },
});
await workflows.open('internment-end', 1);
assert.match(body, /Selecione conforme o contrato/);
assert.match(body, /data-action="preview-settlement"/);
assert.match(body, /name="assinatura" value=""/);
assert.match(body, /DISPENSAR_FUTURAS/);
await workflows.open('internment-extend', 1);
assert.match(body, /name="periodo_atual" value="2"/);
assert.match(body, /name="novo_periodo"/);
await workflows.open('refund', 3);
assert.match(body, /name="multa_juros"/);
assert.match(body, /data-endpoint="\/api\/recebimentos\/devolver"/);
await workflows.open('wallet-refund', 2);
assert.doesNotMatch(body, /name="multa_juros"/);
await workflows.open('refund-reversal', 2);
assert.match(body, /devolução foi lançada por engano/);
await workflows.open('contact-primary', 1);
assert.match(body, /name="responsavel_id"/);
await workflows.open('recurrence', 4);
assert.match(body, /name="data_fim"/);
await workflows.open('recurrence-generate', 4);
assert.match(body, /Contas já existentes/);
const original = globalThis.FormData;
globalThis.FormData = class { get(name) { return { id: 1, data_encerramento: '2026-09-12', politica: 'DISPENSAR_FUTURAS' }[name]; } };
const target = { innerHTML: '', textContent: '' }, signature = { value: '' };
try {
    await workflows.preview({querySelector: () => target, elements: {assinatura: signature}});
    assert.equal(signature.value, 'assinatura-conferida');
    assert.match(target.innerHTML, /Faça as devoluções/);
    assert.match(target.innerHTML, /Permanece uma dívida da carteira/);
} finally { globalThis.FormData = original; }
console.log('Formulários de acerto, devolução, recorrência e prorrogação validados.');

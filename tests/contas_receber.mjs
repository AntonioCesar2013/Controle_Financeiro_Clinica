import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import { createResidentDocuments, printDocument } from '../frontend/js/components/resident-documents.js';
import { renderActionTable } from '../frontend/js/components/renderers.js';
import { formatMoney, formatDate, valueOrDash } from '../frontend/js/utils/formatters.js';
import { currencyValue } from '../frontend/js/utils/masks.js';

const source = await readFile(new URL('../frontend/js/app.js', import.meta.url), 'utf8');
function trecho(inicio, fim) {
    const start = source.indexOf(inicio), end = source.indexOf(fim, start + inicio.length);
    assert(start >= 0 && end > start);
    return source.slice(start, end);
}
const ctx = vm.createContext({ currencyValue, Intl });
vm.runInContext(trecho('    function updateSettlementRemaining(', '    function selectOptions('), ctx);
for (const kind of ['recebimento', 'pagamento']) {
    let erroValor, erroDesconto;
    const restante = { value: '' };
    const valor = { value: 'R$ 0,10', setCustomValidity: text => { erroValor = text; } };
    const desconto = { value: 'R$ 0,20', setCustomValidity: text => { erroDesconto = text; } };
    ctx.form = { dataset: { kind }, querySelector: selector => selector === '[data-remaining]'
        ? { dataset: { remaining: '0.30' } } : restante, elements: { valor, desconto, multa_juros: { value: 'R$ 5,00' } } };
    vm.runInContext('updateSettlementRemaining(form)', ctx);
    assert.equal(erroValor, ''); assert.equal(erroDesconto, '');
    assert.match(restante.value, /0,00/);
    desconto.value = 'R$ 0,21';
    vm.runInContext('updateSettlementRemaining(form)', ctx);
    assert.match(erroValor, /ultrapassar/);
    desconto.value = 'R$ 0,20';
    vm.runInContext('updateSettlementRemaining(form)', ctx);
    assert.equal(erroValor, ''); assert.equal(erroDesconto, '');
    valor.value = 'R$ 0,09';
    vm.runInContext('updateSettlementRemaining(form)', ctx);
    assert.match(restante.value, /0,01/);
}

const panelCtx = vm.createContext({ api: async path => ({ dados: path === '/api/mensalidades'
    ? [{ id: 1, status: 'ABERTA', saldo_restante: 10000, data_vencimento: '2026-09-16' },
       { id: 2, status: 'PAGA', saldo_restante: 0, data_vencimento: '2026-09-16' }]
    : [{ id: 1, status: 'ABERTA', saldo_restante: 10000, data_vencimento: '2026-09-16' },
       { id: 2, status: 'DESCONTADA', saldo_restante: 0, data_vencimento: '2026-09-16' }] }),
    renderActionTable, formatMoney, formatDate, valueOrStatus: valueOrDash,
    localDate: () => '2026-09-16' });
vm.runInContext(trecho('    async function renderReceivables()', '    async function renderPayables()'), panelCtx);
for (const method of ['renderReceivables()', 'renderMonthlyFees()']) {
    const html = await vm.runInContext(method, panelCtx);
    assert.match(html, /data-kind="desconto(?:_mensalidade)?"/);
    assert.match(html, /data-selection-action="discount"/);
    assert(!html.includes('data-kind="desconto" data-id="2"'));
    assert(!html.includes('data-kind="desconto_mensalidade" data-id="2"'));
}

let html;
const docs = createResidentDocuments({
    api: async () => ({ dados: { residente: { nome: 'Teste', cpf: '12345678901' },
        resumo: { devolvido_periodo: 300 }, cobrancas: [], recebimentos: [], movimentacoes_carteira: [],
        devolucoes: [{ data_devolucao: '2026-09-16', total_lancamento: 400, motivo: 'Erro', documento: 'D1', estornada: 1,
            estornada_em: '2026-09-16 10:00:00', motivo_estorno: 'Registro equivocado' },
            { data_devolucao: '2026-09-16', total_lancamento: 300, motivo: 'Parcial', documento: 'D2', estornada: 0 }] } }),
    showPanel: (_, body) => { html = body; }, showAlert: (_, error) => { throw Error(error); },
});
await docs.openStatement(1);
const devolucoes = html.split('<h3>Devoluções do tratamento</h3>')[1].split('<h3>Carteira')[0];
assert.match(devolucoes, /ESTORNADA/);
assert.match(devolucoes, /Registro equivocado/);
assert.match(devolucoes, /16\/09\/2026/);
assert.match(devolucoes, /3,00/);
assert.match(devolucoes, /EFETIVA/);
const clone = { innerHTML: html, querySelectorAll: () => [] };
let printTarget;
globalThis.document = { querySelector: () => null, createElement: () => ({ append: node => { printTarget = node; }, querySelectorAll: () => [] }), body: { append: () => {} } };
globalThis.window = { addEventListener: () => {}, print: () => {} };
printDocument({ querySelector: () => ({ cloneNode: () => clone }) });
assert.match(printTarget.innerHTML, /ESTORNADA/);
assert.match(printTarget.innerHTML, /Registro equivocado/);
console.log('Contas a receber: centavos, ações elegíveis, extrato em tela e impressão validados.');

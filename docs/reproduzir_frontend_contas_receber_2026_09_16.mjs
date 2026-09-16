// Funções reais com dependências simuladas; asserções do comportamento defeituoso.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import { createResidentDocuments } from '../frontend/js/components/resident-documents.js';
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
let erro;
const saldo = { value: '' };
ctx.form = {
    querySelector: selector => selector === '[data-remaining]' ? { dataset: { remaining: '0.30' } } : saldo,
    elements: { valor: {value: 'R$ 0,10', setCustomValidity: text => { erro = text; }}, desconto: {value: 'R$ 0,20', setCustomValidity: () => {}} },
};
vm.runInContext('updateSettlementRemaining(form)', ctx);
assert.match(erro, /ultrapassar/);
console.log('Confirmado: 0,10 recebido + 0,20 desconto sobre saldo 0,30 gera erro:', erro);

const history = renderActionTable([{ valor: 1000, multa_juros: 150, estornada: true }], [['Total recebido', 'total_lancamento', formatMoney]], () => '');
assert.match(history, /0,00/);
console.log('Confirmado: histórico sem total_lancamento exibe 0,00 para principal + juros de 11,50.');

let html;
const documents = createResidentDocuments({
    api: async () => ({ dados: {
        residente: { nome: 'Teste', cpf: '12345678901' }, resumo: { recebido_periodo: 1000, devolvido_periodo: 0 },
        cobrancas: [], recebimentos: [], movimentacoes_carteira: [],
        devolucoes: [{ data_devolucao: '2026-09-16', total_lancamento: 400, motivo: 'Teste', documento: 'D-1', estornada: 1, motivo_estorno: 'Registro incorreto' }],
    } }),
    showPanel: (_, body) => { html = body; }, showAlert: (_, erro) => { throw Error(erro); },
});
await documents.openStatement(1);
const devolucoesHtml = html.split('<h3>Devoluções do tratamento</h3>')[1].split('<h3>Carteira')[0];
assert.match(devolucoesHtml, /4,00/);
assert(!/estorn|Registro incorreto/i.test(devolucoesHtml));
console.log('Confirmado: extrato exibe devolução de 4,00 corrigida sem situação nem motivo do estorno.');

const panelCtx = vm.createContext({
    api: async () => ({ dados: [{ id: 1, status: 'ABERTA', saldo_restante: 10000, data_vencimento: '2026-09-16' }] }),
    renderActionTable, formatMoney, formatDate, valueOrStatus: valueOrDash,
});
vm.runInContext(trecho('    async function renderReceivables()', '    function monthlyStatus('), panelCtx);
const panel = await vm.runInContext('renderReceivables()', panelCtx);
assert(!panel.includes('data-kind="desconto"'));
assert(!source.includes('data-kind="desconto"'));
console.log('Confirmado: não há ação de desconto independente nas telas, embora exista formulário/rota para isso.');

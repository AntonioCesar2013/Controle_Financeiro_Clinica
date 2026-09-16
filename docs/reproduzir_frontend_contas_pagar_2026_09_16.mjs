// Executa funções reais extraídas do app com dependências simuladas; não abre navegador.
// As asserções confirmam o comportamento defeituoso encontrado na auditoria.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = await readFile(new URL('../frontend/js/app.js', import.meta.url), 'utf8');
function trecho(inicio, fim) {
    const start = source.indexOf(inicio);
    const end = source.indexOf(fim, start + inicio.length);
    assert(start >= 0 && end > start);
    return source.slice(start, end);
}
let url;
const ctx = vm.createContext({
    URLSearchParams,
    payableState: { pagina: 1, busca: '', status: '', inicio: '2026-02-01', fim: '2026-02-28', ordem: 'vencimento_asc' },
    api: async path => {
        url = path;
        return { dados: { linhas: [], total_filtrado: 0, total_registros: 0, tamanho: 50, pagina: 1, totais_filtrados: { restante: 0 } } };
    },
    renderActionTable: () => '', formatDate: String, formatMoney: String, escapeHtml: String,
});
vm.runInContext(trecho('    async function renderPayables()', '    async function renderExpenses()'), ctx);
await vm.runInContext('renderPayables()', ctx);
const query = new URL(url, 'http://localhost').searchParams;
assert.equal(query.get('inicio'), '2026-02-01');
assert.equal(query.get('data_inicio'), null);
console.log('Confirmado: renderPayables envia inicio/fim, não data_inicio/data_fim:', url);

let panel;
const formCtx = vm.createContext({
    api: async () => ({ dados: { setores: [{ id: 1, nome: 'Inativo', ativo: 0 }], despesas: [{ id: 2, setor_id: 1, setor_nome: 'Inativo', descricao: 'Conta teste', ativo: 1 }] } }),
    localDate: () => '2026-09-16', escapeHtml: String, moneyField: () => '',
    createPanel: args => args,
    layers: { auxiliary: { replaceChildren: p => { panel = p; }, querySelector: () => null } },
    requestAnimationFrame: fn => fn(),
    showAlert: (_, text) => { throw new Error(text); },
});
vm.runInContext(trecho('    async function openFinancialForm(', '    function moneyField('), formCtx);
await vm.runInContext("openFinancialForm('conta')", formCtx);
assert.match(panel.body, /<option value="2">Conta teste — Inativo<\/option>/);
console.log('Confirmado: Nova conta oferece despesa de setor inativo.');

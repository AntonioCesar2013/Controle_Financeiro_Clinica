import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import { renderActionTable } from '../frontend/js/components/renderers.js';
import { escapeHtml, formatActive, formatCpf, formatDate, formatDateTime, valueOrDash } from '../frontend/js/utils/formatters.js';

const source = await readFile(new URL('../frontend/js/app.js', import.meta.url), 'utf8');
function trecho(inicio, fim) {
    const start = source.indexOf(inicio), end = source.indexOf(fim, start + inicio.length);
    assert(start >= 0 && end > start);
    return source.slice(start, end);
}
let panel;
const items = [{ id: 9, residente_id: 1, nome: 'Mala <azul>', quantidade: 2, descricao: 'Pertence pessoal',
    data_entrada: '2026-09-10', data_retirada: '2026-09-16' }];
const residents = [{ id: 1, nome: 'Ana <teste>', cpf: '12345678901', ativo: 1 }];
const ctx = vm.createContext({
    api: async path => ({ dados: path.startsWith('/api/residentes/itens') ? items : residents }),
    layers: { auxiliary: { replaceChildren: value => { panel = value; } } },
    createPanel: value => value, renderActionTable, escapeHtml, formatActive, formatCpf,
    formatDate, formatDateTime, valueOrDash, showAlert: (_, error) => { throw Error(error); },
    localDate: () => '2026-09-16', workflows: { open: () => {} },
});
vm.runInContext(trecho('    async function openMaintenanceForm(', '    function activeSelect('), ctx);
vm.runInContext(trecho('    async function openResidentItems(', '    async function submitResident('), ctx);
vm.runInContext(trecho('    async function renderResidents()', '    async function renderGuardians()'), ctx);
const residentsHtml = await vm.runInContext('renderResidents()', ctx);
assert.match(residentsHtml, /data-action="select-report-row" data-row-id="1"/);
assert.match(residentsHtml, /data-capabilities="edit contact items statement"/);
assert.match(residentsHtml, /data-action="resident-items" data-selection-action="items" disabled/);
assert.match(residentsHtml, /data-selection-action="edit" disabled/);
assert.match(residentsHtml, /data-selection-action="contact" disabled/);
assert.match(residentsHtml, /data-selection-action="statement" disabled/);
assert.doesNotMatch(residentsHtml, /data-column-key="acoes"/);
vm.runInContext(trecho('    function selectReportRow(', '    async function updateDashboardChart('), ctx);
const buttons = ['edit', 'contact', 'items', 'statement'].map(selectionAction => ({
    dataset: { selectionAction }, disabled: true,
}));
const row = {
    dataset: { rowId: '1', capabilities: 'edit contact items statement' },
    selected: 'false', getAttribute: () => row.selected,
    setAttribute: (_, value) => { row.selected = value; },
    closest: selector => selector === '.selection-scope'
        ? { querySelectorAll: () => buttons }
        : selector === 'tbody' ? { querySelectorAll: () => [] } : null,
};
ctx.row = row;
vm.runInContext('selectReportRow(row)', ctx);
assert(buttons.every(button => !button.disabled && button.dataset.id === '1'));
vm.runInContext('selectReportRow(row)', ctx);
assert(buttons.every(button => button.disabled && !('id' in button.dataset)));
await vm.runInContext('openResidentItems(1)', ctx);
assert.match(panel.body, /Mala &lt;azul&gt;/);
assert.match(panel.body, /10\/09\/2026/);
assert.match(panel.body, /16\/09\/2026/);
assert.match(panel.body, /data-resident-id="1"/);
assert.match(panel.body, /Adicionar item/);
await vm.runInContext('openMaintenanceForm("resident-item-new", 1)', ctx);
assert.match(panel.body, /name="residente_id" value="1"/);
assert.match(panel.body, /name="quantidade"/);
assert.match(panel.body, /name="data_entrada" type="date" value="2026-09-16"/);
assert.match(panel.body, /name="data_retirada" type="date"/);
await vm.runInContext('openMaintenanceForm("resident-item", 9, 1)', ctx);
assert.match(panel.body, /name="id" value="9"/);
assert.match(panel.body, /Mala &lt;azul&gt;/);
assert.match(panel.body, /name="data_entrada" type="date" value="2026-09-10"/);
assert.match(panel.body, /name="data_retirada" type="date" value="2026-09-16"/);
console.log('Itens pessoais: lista, vínculo, formulário novo e edição validados.');

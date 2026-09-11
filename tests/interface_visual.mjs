import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { renderActionTable } from "../frontend/js/components/renderers.js";

const base = await readFile(new URL("../frontend/css/base.css", import.meta.url), "utf8");
const layout = await readFile(new URL("../frontend/css/layout.css", import.meta.url), "utf8");
const responsive = await readFile(new URL("../frontend/css/responsive.css", import.meta.url), "utf8");
const app = await readFile(new URL("../frontend/js/app.js", import.meta.url), "utf8");

assert.doesNotMatch(base, /transform:\s*scale\(/, "a interface não deve usar escala global");
assert.match(base, /--sidebar-width:\s*clamp\(/, "a barra lateral deve possuir limites fluidos");
assert.match(responsive, /max-width:\s*760px/, "o layout deve reorganizar a navegação em telas estreitas");
assert.match(layout, /menu-group__title/, "o menu deve possuir títulos de grupos");
for (const group of ["Visão geral", "Módulos", "Pessoas", "Atendimento", "Operação", "Estoque", "Acesso", "Sistema"]) {
    assert(app.includes(`\"${group}\"`), `o menu deve incluir o grupo ${group}`);
}
assert.match(app, /\["carteiras", "Carteiras", "Créditos, saldos e compras", "open-panel", "Residentes"\]/);
assert.match(app, /data-dashboard-chart-start/);
assert.match(app, /data-dashboard-chart-end/);
assert.match(app, /new Date\(currentYear, currentMonth, 0\)/, "o gráfico deve iniciar com o mês civil atual completo");
assert.match(app, /openStartupDueAlert/, "o sistema deve exibir o aviso financeiro ao iniciar");
assert.match(app, /setDate\(limitDate\.getDate\(\) \+ 5\)/, "o aviso deve considerar os próximos cinco dias");
assert.match(app, /Contas que exigem atenção/, "o aviso deve identificar claramente as contas críticas");

const html = renderActionTable(
    [{ nome: "Conta", status: "VENCIDA", valor: 12550 }],
    [["Nome", "nome"], ["Situação", "status"], ["Valor", "valor"]],
    () => '<button type="button">Abrir</button>',
);
assert.match(html, /status--danger/);
assert.match(html, /data-column-type="money"/);
assert.match(html, /data-column-key="status"/);
assert.match(html, /clear-table-filters/);

const selectable = renderActionTable(
    [{ id: 7, descricao: "Energia", status: "ABERTA" }],
    [["Descrição", "descricao"], ["Status", "status"]],
    () => '<button type="button">Pagar</button>',
    { selectableRows: true, selectionData: (row) => ({ id: row.id, capabilities: ["pay", "history"] }) },
);
assert.match(selectable, /data-action="select-report-row"/);
assert.match(selectable, /data-capabilities="pay history"/);
assert.doesNotMatch(selectable, /<th>Ações<\/th>/);

console.log("Layout fluido, status, valores e controles das tabelas validados.");

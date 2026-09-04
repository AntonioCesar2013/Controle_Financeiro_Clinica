import assert from "node:assert/strict";
import { businessModules } from "../frontend/js/modules/index.js";
import { createPanelRegistry, resolvePanel } from "../frontend/js/core/router.js";
import { can } from "../frontend/js/core/permissions.js";
import { renderActionTable } from "../frontend/js/components/renderers.js";
import { currencyValue, maskCurrency } from "../frontend/js/utils/masks.js";

const renderers = new Proxy({}, { get: (_, name) => () => name });
const panels = createPanelRegistry(businessModules, renderers);
assert.deepEqual(businessModules.map((m) => m.name), ["cadastros", "financeiro", "cantina"]);
for (const name of ["residentes", "internacoes", "contas_receber", "cantina", "itens"]) {
    assert(resolvePanel(panels, name), `painel ${name} deve estar registrado`);
}
assert.equal(can("financeiro.pagar"), true);
const filteredTable = renderActionTable(
    [{ status: "PAGA", nome: "Teste" }],
    [["Nome", "nome"], ["Situação", "status"]],
    () => "",
    { allStatusesLabel: "Todas as mensalidades", statuses: [["A VENCER", "A pagar"], ["PAGA", "Pagas"]] },
);
assert.match(filteredTable, /Todas as mensalidades/);
assert.match(filteredTable, /value="A VENCER">A pagar/);
assert.equal(maskCurrency("123456"), "R$ 1.234,56");
assert.equal(currencyValue("R$ 1.234,56"), 1234.56);
console.log("Registro modular, painéis e extensão de permissões do frontend validados.");

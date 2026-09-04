import assert from "node:assert/strict";
import { businessModules } from "../frontend/js/modules/index.js";
import { createPanelRegistry, resolvePanel } from "../frontend/js/core/router.js";
import { can } from "../frontend/js/core/permissions.js";

const renderers = new Proxy({}, { get: (_, name) => () => name });
const panels = createPanelRegistry(businessModules, renderers);
assert.deepEqual(businessModules.map((m) => m.name), ["cadastros", "financeiro", "cantina"]);
for (const name of ["residentes", "internacoes", "contas_receber", "cantina", "itens"]) {
    assert(resolvePanel(panels, name), `painel ${name} deve estar registrado`);
}
assert.equal(can("financeiro.pagar"), true);
console.log("Registro modular, painéis e extensão de permissões do frontend validados.");

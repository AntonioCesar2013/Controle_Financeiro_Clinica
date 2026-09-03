import assert from "node:assert/strict";
import { createResidentDocuments } from "../frontend/js/components/resident-documents.js";
import { renderActionTable } from "../frontend/js/components/renderers.js";
let html = "";
const docs = createResidentDocuments({
    api: async () => ({dados: {id: 1, numero: "REC-000001", recebimento_id: 2, emitido_em: "2026-09-03 12:00:00", cancelado: false,
        dados: {valor: 12550, valor_devido: 30000, residente_nome: "José <script>", residente_cpf: "12345678901", responsavel_nome: "Responsável", numero_parcela: 1, internacao_id: 1, forma_recebimento: "PIX", data_recebimento: "2026-09-03", data_vencimento: "2026-09-10"}}}),
    showPanel: (_, body) => { html = body; },
    showAlert: (_, error) => { throw new Error(error); },
});
await docs.openReceipt(2);
assert(html.includes("125,50"));
assert(html.includes("Pagamento parcial"));
assert(html.includes("REC-000001"));
assert(!html.includes("José <script>"));
assert(html.includes("José &lt;script&gt;"));
const table = renderActionTable([{nome: 'José "teste"', status: "ATIVO", data_vencimento: "2026-09-10"}], [["Nome", "nome"], ["Status", "status"], ["Vencimento", "data_vencimento"]], () => "");
assert(table.includes("data-filter-start"));
assert(table.includes("data-filter-status"));
assert(table.includes("&quot;teste&quot;"));
console.log("Recibo parcial, formatação de centavos, escape HTML e controles da tabela validados.");

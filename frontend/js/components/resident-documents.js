import { escapeHtml as e, formatMoney as money, formatDate as date, formatDateTime, formatCpf, localDate } from "../utils/formatters.js";
import { renderTable, renderActionTable, metric } from "./renderers.js";

export function createResidentDocuments({ api, showPanel, showAlert }) {
    async function statementBody(id, start = "", end = "") {
        const query = new URLSearchParams({ id });
        if (start) query.set("data_inicio", start);
        if (end) query.set("data_fim", end);
        const { dados: d } = await api(`/api/residentes/extrato?${query}`);
        const r = d.resumo;
        const controls = `<div class="document-controls"><label>De<input type="date" data-statement-start value="${e(start)}"></label><label>Até<input type="date" data-statement-end value="${e(end)}"></label><button class="button" data-action="filter-statement" data-id="${e(id)}">Aplicar período</button><button class="button button--secondary" data-action="print-document">Imprimir / salvar PDF</button></div>`;
        const charges = renderTable(d.cobrancas, [["Internação", "internacao_id"], ["Parcela", "numero_parcela"], ["Tipo", "tipo"], ["Vencimento", "data_vencimento", date], ["Devido", "valor_devido", money], ["Recebido", "total_recebido", money], ["Pendente", "saldo_restante", money]]);
        const payments = renderActionTable(d.recebimentos, [["Data", "data_recebimento", date], ["Parcela", "numero_parcela"], ["Valor", "valor", money], ["Forma", "forma_recebimento"], ["Estorno", "estornada", v => v ? "Estornado" : "Efetivo"]], row => !row.estornada && row.tipo === "MENSALIDADE" ? `<button class="button" data-action="generate-receipt" data-id="${row.id}">Gerar recibo</button>` : "");
        const wallet = renderTable(d.movimentacoes_carteira, [["Data", "data_movimentacao", date], ["Tipo", "tipo"], ["Produto", "item_nome"], ["Valor", "valor_total", money], ["Situação", "estornada", v => v ? "Estornada" : "Efetiva"], ["Saldo após", "saldo_apos", money]]);
        return `${controls}<article class="resident-document"><header><h2>Extrato por residente</h2><h3>${e(d.residente.nome)}</h3><p>CPF: ${e(formatCpf(d.residente.cpf))}</p><p>Período: ${start ? date(start) : "Início dos registros"} a ${end ? date(end) : "Último registro"} · Emitido em ${date(localDate())}</p></header><div class="metrics">${metric("Recebido no período", r.recebido_periodo, "success")}${metric("Pendente das cobranças do período", r.pendente_periodo, "warning")}${metric("Pendente total de tratamento", r.pendente_total, "warning")}${metric("Saldo atual da carteira", r.carteira_atual, r.carteira_atual < 0 ? "danger" : "primary")}</div><p>O tratamento e a carteira são controles separados. Saldo negativo da carteira é valor a cobrar dos responsáveis.</p><h3>Cobranças — por vencimento</h3><p>Os saldos refletem recebimentos e descontos registrados até agora.</p>${charges}<h3>Recebimentos — por data de pagamento</h3>${payments}<h3>Carteira — por data da movimentação</h3><p>Saldo de abertura: ${money(r.carteira_abertura)} · Saldo de fechamento: ${money(r.carteira_fechamento)}</p><p>Saldos recalculados conforme os lançamentos válidos atualmente. Movimentos estornados não alteram o saldo.</p>${wallet}</article>`;
    }

    async function openStatement(id, start = "", end = "") {
        try { showPanel("Extrato do residente", await statementBody(id, start, end)); }
        catch (error) { showAlert("Não foi possível consultar", error.message); }
    }

    async function openReceipt(recebimentoId) {
        try {
            const { dados: r } = await api("/api/recibos", {method: "POST", body: {recebimento_id: recebimentoId}});
            const d = r.dados;
            const body = `<div class="document-controls"><button class="button" data-action="print-document">Imprimir / salvar PDF</button></div><article class="resident-document receipt"><header><p>Clínica da Cruz</p><h2>Recibo de pagamento de mensalidade</h2><strong>${e(r.numero)}</strong></header>${r.cancelado ? "<h2>RECIBO CANCELADO — RECEBIMENTO ESTORNADO</h2>" : ""}<p class="receipt-value">${money(d.valor)}</p><p>Recebemos o valor de <strong>${money(d.valor)}</strong>, em <strong>${date(d.data_recebimento)}</strong>, referente à mensalidade de <strong>${e(d.residente_nome)}</strong>, CPF ${e(formatCpf(d.residente_cpf))}.</p><dl><dt>Internação / parcela</dt><dd>${e(d.internacao_id)} / ${e(d.numero_parcela)}</dd><dt>Vencimento da mensalidade</dt><dd>${date(d.data_vencimento)}</dd><dt>Forma de recebimento</dt><dd>${e(d.forma_recebimento)}</dd><dt>Responsável cadastrado</dt><dd>${e(d.responsavel_nome)} · CPF ${e(formatCpf(d.responsavel_cpf))}</dd><dt>Identificação do recebimento</dt><dd>${e(r.recebimento_id)}</dd></dl><p>Este recibo corresponde exclusivamente ao valor recebido acima.</p>${d.valor < d.valor_devido ? `<p>Pagamento parcial em relação ao valor da mensalidade (${money(d.valor_devido)}).</p>` : ""}<p>${e(d.observacao || "")}</p><p>Emitido em ${formatDateTime(r.emitido_em)}</p><div class="receipt-signature">Assinatura do responsável pelo recebimento<br>Clínica da Cruz</div></article>`;
            showPanel("Recibo de mensalidade", body);
        } catch (error) { showAlert("Não foi possível gerar o recibo", error.message); }
    }
    return { openStatement, openReceipt };
}

export function printDocument(panel) {
    const document = panel.querySelector(".resident-document");
    if (!document) return;
    globalThis.document.querySelector("#document-print-target")?.remove();
    const target = globalThis.document.createElement("section");
    target.id = "document-print-target";
    target.append(document.cloneNode(true));
    // O extrato impresso contém todos os registros do período selecionado.
    target.querySelectorAll("tr[hidden]").forEach(row => row.removeAttribute("hidden"));
    globalThis.document.body.append(target);
    window.addEventListener("afterprint", () => target.remove(), { once: true });
    window.print();
}

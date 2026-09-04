export const financeiroModule = {
    name: "financeiro",
    panels: (r) => ({
        financeiro: ["Financeiro", "Operações financeiras", r.renderDashboard],
        contas_receber: ["Contas a receber", "Financeiro", r.renderReceivables],
        mensalidades: ["Mensalidades", "Controle por residente", r.renderMonthlyFees],
        contas_pagar: ["Contas a pagar", "Financeiro", r.renderPayables],
        caixa: ["Fluxo de caixa", "Financeiro", r.renderCashFlow],
        despesas: ["Despesas", "Financeiro", r.renderExpenses],
    }),
};

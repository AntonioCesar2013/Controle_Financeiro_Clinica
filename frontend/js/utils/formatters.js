const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function formatMoney(value) {
    return currency.format(Number(value || 0) / 100);
}

export function formatReais(value) {
    return currency.format(Number(value || 0));
}

export function formatOptionalReais(value) {
    return value === null || value === undefined || value === "" ? "—" : formatReais(value);
}

export function formatDate(value) {
    if (!value) return "—";
    const [year, month, day] = String(value).slice(0, 10).split("-");
    return year && month && day ? `${day}/${month}/${year}` : String(value);
}

export function formatDateTime(value) {
    return value ? `${formatDate(value)} ${String(value).slice(11, 16)}`.trim() : "—";
}

export function formatCpf(value) {
    const digits = String(value || "").replace(/\D/g, "");
    return digits.length === 11
        ? digits.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4")
        : valueOrDash(value);
}

export function formatActive(value) {
    return Number(value) === 1 ? "Ativo" : "Inativo";
}

export function formatYesNo(value) {
    return Number(value) === 1 ? "Sim" : "Não";
}

export function formatReversal(value) {
    return Number(value) === 1 ? "Estornada" : "Válida";
}

export function valueOrStatus(value, row) {
    return valueOrDash(value || row.status);
}

export function valueOrDash(value) {
    return value === null || value === undefined || value === "" ? "—" : String(value);
}

export function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "'": "&#39;",
        "\"": "&quot;",
    })[char]);
}

export function normalizeSearch(value) {
    return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .toLocaleLowerCase("pt-BR").replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

export function matchesFilters(row, { search = "", status = "", start = "", end = "" }) {
    const tokens = normalizeSearch(search).split(/\s+/).filter(Boolean);
    return tokens.every(token => normalizeSearch(row.search).includes(token))
        && (!status || row.status === status)
        && (!start || row.date >= start) && (!end || row.date <= end);
}

export function applyTableFilters(control) {
    const container = control.closest(".filterable");
    if (!container) return;
    const fields = { search: container.querySelector("[data-filter-search]")?.value || "",
        status: container.querySelector("[data-filter-status]")?.value || "",
        start: container.querySelector("[data-filter-start]")?.value || "",
        end: container.querySelector("[data-filter-end]")?.value || "" };
    const invalid = fields.start && fields.end && fields.start > fields.end;
    let count = 0;
    container.querySelectorAll("tbody tr[data-search]").forEach(row => {
        row.hidden = Boolean(invalid) || !matchesFilters({search: row.dataset.search, status: row.dataset.status, date: row.dataset.date}, fields);
        if (!row.hidden) count++;
    });
    container.querySelector("[data-filter-count]").textContent = invalid
        ? "A data inicial não pode ser posterior à final."
        : `${count} registro(s) encontrado(s). Filtros aplicados à tabela.`;
}

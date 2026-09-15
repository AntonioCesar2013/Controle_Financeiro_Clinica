export function normalizeSearch(value) {
    return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .toLocaleLowerCase("pt-BR").replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

const normalizedRows = new WeakMap();
const filterTimers = new WeakMap();

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
        let search = normalizedRows.get(row);
        if (search === undefined) {
            search = normalizeSearch(row.dataset.search);
            normalizedRows.set(row, search);
        }
        const tokens = normalizeSearch(fields.search).split(/\s+/).filter(Boolean);
        row.hidden = Boolean(invalid) || !tokens.every(token => search.includes(token))
            || Boolean(fields.status && row.dataset.status !== fields.status)
            || Boolean(fields.start && row.dataset.date < fields.start)
            || Boolean(fields.end && row.dataset.date > fields.end);
        if (row.hidden && row.matches(".selectable-row[aria-selected='true']")) row.click();
        if (!row.hidden) count++;
    });
    container.querySelector("[data-filter-count]").textContent = invalid
        ? "A data inicial não pode ser posterior à final."
        : `${count} registro(s) encontrado(s). Filtros aplicados à tabela.`;
}

export function scheduleTableFilters(control, delay = 200) {
    const container = control.closest(".filterable");
    if (!container) return;
    clearTimeout(filterTimers.get(container));
    filterTimers.set(container, setTimeout(() => {
        filterTimers.delete(container);
        if (control.isConnected) applyTableFilters(control);
    }, delay));
}

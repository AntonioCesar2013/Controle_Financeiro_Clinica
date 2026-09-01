import { escapeHtml, formatMoney, valueOrDash } from "../utils/formatters.js";

export function renderTable(rows, columns) {
    if (!rows?.length) return emptyState();
    return `<div class="table-wrap"><table><thead><tr>${columns.map(([label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${columns.map(([, key, formatter]) => `<td>${escapeHtml(formatter ? formatter(row[key], row) : valueOrDash(row[key]))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

export function renderActionTable(rows, columns, actions) {
    if (!rows?.length) return emptyState();
    return `<div class="table-wrap"><table><thead><tr>${columns.map(([label]) => `<th>${label}</th>`).join("")}<th>Ações</th></tr></thead><tbody>${rows.map((row) => `<tr>${columns.map(([, key, formatter]) => `<td>${escapeHtml(formatter ? formatter(row[key], row) : valueOrDash(row[key]))}</td>`).join("")}<td><div class="report-actions">${actions(row)}</div></td></tr>`).join("")}</tbody></table></div>`;
}

export function metric(label, value, tone) {
    return `<article class="metric metric--${tone}"><span class="metric__label">${label}</span><strong class="metric__value">${formatMoney(value)}</strong></article>`;
}

export function loadingState() {
    return '<div class="placeholder"><div><h3>Carregando</h3><p>Consultando dados do sistema…</p></div></div>';
}

export function emptyState(title = "Nenhum registro encontrado", message = "Não há dados cadastrados para esta consulta.") {
    return `<div class="placeholder"><div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(message)}</p></div></div>`;
}

export function errorState(message) {
    return `<div class="placeholder"><div><h3>Não foi possível carregar</h3><p>${escapeHtml(message)}</p></div></div>`;
}

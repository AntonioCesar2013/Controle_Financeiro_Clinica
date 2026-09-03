import { escapeHtml, formatMoney, valueOrDash } from "../utils/formatters.js";

export function renderTable(rows, columns) {
    if (!rows?.length) return emptyState();
    return `<div class="table-wrap"><table><thead><tr>${columns.map(([label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${columns.map(([, key, formatter]) => `<td>${escapeHtml(formatter ? formatter(row[key], row) : valueOrDash(row[key]))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

export function renderActionTable(rows, columns, actions) {
    if (!rows?.length) return emptyState();
    const statusColumn = columns.find(([, key]) => ["ativo", "status", "situacao_temporal", "estornada"].includes(key));
    const dateColumn = columns.find(([, key]) => ["data_vencimento", "data_acolhimento", "data_recebimento", "data_pagamento", "data_movimentacao"].includes(key));
    const status = row => statusColumn ? String(statusColumn[2] ? statusColumn[2](row[statusColumn[1]], row) : row[statusColumn[1]] ?? "") : "";
    const statuses = [...new Set(rows.map(status))].filter(Boolean).sort();
    const controls = `<div class="table-filters"><label>Buscar<input type="search" data-filter-search placeholder="Nome, CPF, descrição…"></label>${statusColumn ? `<label>Situação<select data-filter-status><option value="">Todas</option>${statuses.map(s => `<option>${escapeHtml(s)}</option>`).join("")}</select></label>` : ""}${dateColumn ? `<label>${escapeHtml(dateColumn[0])} de<input type="date" data-filter-start></label><label>Até<input type="date" data-filter-end></label>` : ""}</div><p data-filter-count aria-live="polite">${rows.length} registro(s). Filtros aplicados à tabela.</p>`;
    return `<section class="filterable">${controls}<div class="table-wrap"><table><thead><tr>${columns.map(([label]) => `<th>${label}</th>`).join("")}<th>Ações</th></tr></thead><tbody>${rows.map(row => `<tr data-search="${escapeHtml(Object.values(row).filter(v => typeof v !== "object").join(" "))}" data-status="${escapeHtml(status(row))}" data-date="${escapeHtml(dateColumn ? row[dateColumn[1]] : "")}">${columns.map(([, key, formatter]) => `<td>${escapeHtml(formatter ? formatter(row[key], row) : valueOrDash(row[key]))}</td>`).join("")}<td><div class="report-actions">${actions(row)}</div></td></tr>`).join("")}</tbody></table></div></section>`;
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

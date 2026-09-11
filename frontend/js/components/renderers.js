import { escapeHtml, formatMoney, valueOrDash } from "../utils/formatters.js";

export function renderTable(rows, columns) {
    if (!rows?.length) return emptyState();
    return `<div class="table-wrap"><table><thead><tr>${columns.map(([label, key]) => `<th${cellAttributes(key)}>${label}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${columns.map(([, key, formatter]) => `<td${cellAttributes(key)}>${renderCell(row, key, formatter)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

export function renderActionTable(rows, columns, actions, options = {}) {
    if (!rows?.length) return emptyState();
    const statusColumn = columns.find(([, key]) => ["ativo", "status", "situacao_temporal", "estornada"].includes(key));
    const dateColumn = columns.find(([, key]) => ["data_vencimento", "data_acolhimento", "data_recebimento", "data_pagamento", "data_movimentacao"].includes(key));
    const status = row => statusColumn ? String(statusColumn[2] ? statusColumn[2](row[statusColumn[1]], row) : row[statusColumn[1]] ?? "") : "";
    const statuses = options.statuses || [...new Set(rows.map(status))].filter(Boolean).sort().map(value => [value, value]);
    const controls = `<div class="table-filters"><label>Buscar<input type="search" data-filter-search placeholder="Nome, CPF ou descrição" aria-label="Buscar nesta tabela"></label>${statusColumn ? `<label>Situação<select data-filter-status><option value="">${escapeHtml(options.allStatusesLabel || "Todas")}</option>${statuses.map(([value, label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`).join("")}</select></label>` : ""}${dateColumn ? `<label>${escapeHtml(dateColumn[0])} de<input type="date" data-filter-start></label><label>Até<input type="date" data-filter-end></label>` : ""}</div><div class="filterable__meta"><p class="filterable__count" data-filter-count aria-live="polite">${rows.length} registro(s).</p><button class="button button--secondary button--compact" type="button" data-action="clear-table-filters">Limpar filtros</button></div>`;
    const selectable = Boolean(options.selectableRows);
    const header = `${columns.map(([label, key]) => `<th${cellAttributes(key)}>${label}</th>`).join("")}${selectable ? "" : '<th data-column-key="acoes">Ações</th>'}`;
    const body = rows.map((row) => {
        const cells = columns.map(([, key, formatter]) => `<td${cellAttributes(key)}>${renderCell(row, key, formatter, statusColumn?.[1] === key)}</td>`).join("");
        const attributes = `data-search="${escapeHtml(Object.values(row).filter(v => typeof v !== "object").join(" "))}" data-status="${escapeHtml(status(row))}" data-date="${escapeHtml(dateColumn ? row[dateColumn[1]] : "")}"`;
        if (!selectable) return `<tr ${attributes}>${cells}<td data-column-key="acoes"><div class="report-actions">${actions(row)}</div></td></tr>`;
        const selection = options.selectionData?.(row) || {};
        const capabilities = Array.isArray(selection.capabilities)
            ? selection.capabilities.join(" ")
            : (selection.canManage ? "manage history" : "history");
        return `<tr class="selectable-row" ${attributes} data-action="select-report-row" data-row-id="${escapeHtml(selection.id ?? row.id ?? "")}" data-capabilities="${escapeHtml(capabilities)}" role="button" tabindex="0" aria-selected="false" title="Clique para selecionar este registro">${cells}</tr>`;
    }).join("");
    return `<section class="filterable${selectable ? " filterable--selectable" : ""}">${controls}${selectable ? '<p class="table-interaction-hint">Selecione uma linha para habilitar as ações acima da tabela.</p>' : ""}<div class="table-wrap"><table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table></div></section>`;
}

function cellAttributes(key) {
    const safeKey = escapeHtml(key);
    const type = /valor|saldo|total|recebido|restante|preco|desconto/.test(key) ? ' data-column-type="money"' : "";
    return ` data-column-key="${safeKey}"${type}`;
}

function renderCell(row, key, formatter, isStatus = false) {
    const value = formatter ? formatter(row[key], row) : valueOrDash(row[key]);
    const safe = escapeHtml(value);
    if (!isStatus) return safe;
    const normalized = String(value).toLocaleUpperCase("pt-BR");
    const tone = /VENCID|CANCEL|ESTORN|INATIV|DIVERG|REVISAR/.test(normalized) ? "danger"
        : /PENDENT|ABERTA|A VENCER|PARCIAL|AGENDADA/.test(normalized) ? "warning"
        : /PAGA|ATIV|CONFERIDA|FECHADO|EFETIV/.test(normalized) ? "success" : "neutral";
    return `<span class="status status--${tone}">${safe}</span>`;
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

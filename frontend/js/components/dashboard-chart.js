import { escapeHtml } from "../utils/formatters.js";

const COLORS = ["#2563eb", "#c8102e"];

export function chartData(movements, metric = "daily") {
    const groups = new Map();
    for (const item of movements || []) {
        const key = metric === "payment" ? (item.forma_pagamento || "Não informada") : String(item.data || "").slice(8, 10);
        if (!key) continue;
        const current = groups.get(key) || { entrada: 0, saida: 0 };
        if (item.tipo === "ENTRADA") current.entrada += Number(item.valor || 0);
        if (item.tipo === "SAIDA") current.saida += Number(item.valor || 0);
        groups.set(key, current);
    }
    const labels = [...groups.keys()].sort((a, b) => metric === "payment" ? a.localeCompare(b, "pt-BR") : Number(a) - Number(b));
    if (metric === "balance") {
        let balance = 0;
        return { labels, series: [{ name: "Resultado acumulado", values: labels.map((label) => balance += groups.get(label).entrada - groups.get(label).saida) }] };
    }
    return { labels, series: [
        { name: "Entradas", values: labels.map((label) => groups.get(label).entrada) },
        { name: "Saídas", values: labels.map((label) => groups.get(label).saida) },
    ] };
}

export function renderDashboardChart(movements, metric = "daily", type = "bar") {
    const data = chartData(movements, metric);
    if (!data.labels.length) return '<div class="chart-empty"><strong>Sem movimentações no período</strong><span>O gráfico será exibido quando houver entradas ou saídas neste mês.</span></div>';
    const width = 820, height = 310, left = 64, right = 20, top = 24, bottom = 52;
    const plotWidth = width - left - right, plotHeight = height - top - bottom;
    const values = data.series.flatMap((series) => series.values);
    const minimum = Math.min(0, ...values), maximum = Math.max(0, ...values);
    const range = maximum - minimum || 1;
    const x = (index) => left + (data.labels.length === 1 ? plotWidth / 2 : index * plotWidth / (data.labels.length - 1));
    const y = (value) => top + (maximum - value) * plotHeight / range;
    const baseline = y(0);
    const grid = Array.from({ length: 5 }, (_, index) => {
        const value = maximum - range * index / 4;
        const py = y(value);
        return `<line x1="${left}" y1="${py}" x2="${width - right}" y2="${py}"/><text x="${left - 10}" y="${py + 4}" text-anchor="end">${shortMoney(value)}</text>`;
    }).join("");
    const labelStep = Math.max(1, Math.ceil(data.labels.length / 10));
    const labels = data.labels.map((label, index) => index % labelStep ? "" : `<text x="${x(index)}" y="${height - 22}" text-anchor="middle">${escapeHtml(metric === "payment" ? compactLabel(label) : `${label}/${String(movements[0]?.data || "").slice(5, 7)}`)}</text>`).join("");
    const drawing = type === "bar" ? bars(data, x, y, baseline, plotWidth) : lines(data, x, y, baseline, type === "area");
    const legend = data.series.map((series, index) => `<span><i style="--legend-color:${COLORS[index]}"></i>${escapeHtml(series.name)}</span>`).join("");
    return `<div class="dashboard-chart__legend">${legend}</div><svg class="dashboard-chart__svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Gráfico financeiro do mês"><g class="chart-grid">${grid}</g><line class="chart-axis" x1="${left}" y1="${baseline}" x2="${width - right}" y2="${baseline}"/>${drawing}<g class="chart-labels">${labels}</g></svg>`;
}

function bars(data, x, y, baseline, plotWidth) {
    const slot = Math.min(54, plotWidth / Math.max(data.labels.length, 1) * .72);
    const barWidth = Math.max(4, slot / data.series.length);
    return data.series.map((series, seriesIndex) => series.values.map((value, index) => {
        const py = y(value), height = Math.max(1, Math.abs(baseline - py));
        const px = x(index) - slot / 2 + seriesIndex * barWidth;
        return `<rect class="chart-bar" x="${px}" y="${Math.min(py, baseline)}" width="${Math.max(3, barWidth - 2)}" height="${height}" fill="${COLORS[seriesIndex]}"><title>${escapeHtml(series.name)}: ${shortMoney(value, true)}</title></rect>`;
    }).join("")).join("");
}

function lines(data, x, y, baseline, area) {
    return data.series.map((series, seriesIndex) => {
        const points = series.values.map((value, index) => `${x(index)},${y(value)}`).join(" ");
        const fill = area ? `<polygon points="${x(0)},${baseline} ${points} ${x(series.values.length - 1)},${baseline}" fill="${COLORS[seriesIndex]}" opacity=".1"/>` : "";
        const dots = series.values.map((value, index) => `<circle cx="${x(index)}" cy="${y(value)}" r="4" fill="${COLORS[seriesIndex]}"><title>${escapeHtml(series.name)}: ${shortMoney(value, true)}</title></circle>`).join("");
        return `${fill}<polyline points="${points}" fill="none" stroke="${COLORS[seriesIndex]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${dots}`;
    }).join("");
}

function shortMoney(cents, full = false) {
    const value = Number(cents || 0) / 100;
    if (full) return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
    if (Math.abs(value) >= 1_000_000) return `R$ ${(value / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
    if (Math.abs(value) >= 1_000) return `R$ ${(value / 1_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mil`;
    return `R$ ${value.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
}

function compactLabel(value) {
    const text = String(value);
    return text.length > 13 ? `${text.slice(0, 12)}…` : text;
}

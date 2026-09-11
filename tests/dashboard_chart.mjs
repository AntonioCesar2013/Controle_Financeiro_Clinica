import assert from "node:assert/strict";
import { chartData, renderDashboardChart } from "../frontend/js/components/dashboard-chart.js";

const movements = [
    { data: "2026-09-01", tipo: "ENTRADA", valor: 10000, forma_pagamento: "PIX" },
    { data: "2026-09-01", tipo: "SAIDA", valor: 2500, forma_pagamento: "PIX" },
    { data: "2026-09-03", tipo: "ENTRADA", valor: 5000, forma_pagamento: "Dinheiro <script>" },
];

const daily = chartData(movements, "daily");
assert.deepEqual(daily.labels, ["01", "03"]);
assert.deepEqual(daily.series[0].values, [10000, 5000]);
assert.deepEqual(daily.series[1].values, [2500, 0]);
assert.deepEqual(chartData(movements, "balance").series[0].values, [7500, 12500]);

assert.match(renderDashboardChart(movements, "daily", "bar"), /class="chart-bar"/);
assert.match(renderDashboardChart(movements, "daily", "line"), /<polyline/);
assert.match(renderDashboardChart(movements, "daily", "area"), /<polygon/);
const payment = renderDashboardChart(movements, "payment", "bar");
assert(!payment.includes("<script>"));
assert(payment.includes("&lt;"));
assert.match(renderDashboardChart([], "daily", "bar"), /Sem movimentações/);

console.log("Gráficos do dashboard: dados, tipos, responsividade SVG e escape validados.");

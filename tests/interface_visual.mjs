import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { renderActionTable, renderTable } from "../frontend/js/components/renderers.js";

const base = await readFile(new URL("../frontend/css/base.css", import.meta.url), "utf8");
const layout = await readFile(new URL("../frontend/css/layout.css", import.meta.url), "utf8");
const responsive = await readFile(new URL("../frontend/css/responsive.css", import.meta.url), "utf8");
const auth = await readFile(new URL("../frontend/css/auth.css", import.meta.url), "utf8");
const components = await readFile(new URL("../frontend/css/components.css", import.meta.url), "utf8");
const modules = await readFile(new URL("../frontend/css/modules.css", import.meta.url), "utf8");
const tableLayout = await readFile(new URL("../frontend/css/table-layout.css", import.meta.url), "utf8");
const tableLayoutScript = await readFile(new URL("../frontend/js/components/table-layout.js", import.meta.url), "utf8");
const filtersScript = await readFile(new URL("../frontend/js/components/filters.js", import.meta.url), "utf8");
const app = await readFile(new URL("../frontend/js/app.js", import.meta.url), "utf8");

assert.doesNotMatch(base, /transform:\s*scale\(/, "a interface não deve usar escala global");
assert.match(base, /--sidebar-width:\s*clamp\(/, "a barra lateral deve possuir limites fluidos");
assert.match(responsive, /max-width:\s*760px/, "o layout deve reorganizar a navegação em telas estreitas");
assert.match(layout, /menu-group__title/, "o menu deve possuir títulos de grupos");
for (const group of ["Módulos", "Pessoas", "Atendimento", "Operação", "Estoque", "Acesso", "Sistema"]) {
    assert(app.includes(`\"${group}\"`), `o menu deve incluir o grupo ${group}`);
}
assert.doesNotMatch(app, /\["dashboard", "Dashboard", "Indicadores e movimentos"/, "menu geral não deve exibir o botão Dashboard");
assert.match(app, /\["financeiro", "Visão financeira"[^\n]+\n\s*\["relatorios", "Relatórios", "Análises por período", "open-panel", "Resumo"\]/, "Relatórios deve ficar imediatamente abaixo de Visão financeira");
assert.match(app, /\["carteiras", "Carteiras", "Créditos, saldos e compras", "open-panel", "Residentes"\]/);
assert.match(app, /data-dashboard-chart-start/);
assert.match(app, /data-dashboard-chart-end/);
assert.match(app, /new Date\(currentYear, currentMonth, 0\)/, "o gráfico deve iniciar com o mês civil atual completo");
assert.match(app, /openStartupDueAlert/, "o sistema deve exibir o aviso financeiro ao iniciar");
assert.match(app, /setDate\(limitDate\.getDate\(\) \+ 5\)/, "o aviso deve considerar os próximos cinco dias");
assert.match(app, /Contas que exigem atenção/, "o aviso deve identificar claramente as contas críticas");
assert.match(app, /organizeTablePanels\(panel\)/, "a organização deve ocorrer depois do carregamento do painel");
assert.match(app, /sameOpenPanel[\s\S]*captureTableFilters\(layers\.main\)[\s\S]*restoreTableFilters\(panel, preservedFilters\)/, "filtros devem sobreviver às atualizações do painel enquanto ele permanecer aberto");
assert.match(filtersScript, /export function captureTableFilters/, "o estado dos filtros deve poder ser capturado antes da atualização");
assert.match(filtersScript, /export function restoreTableFilters[\s\S]*applyTableFilters\(control\)/, "filtros restaurados devem ser reaplicados à tabela");
assert.match(app, /data-action="clear-payables-filters"/, "contas a pagar deve oferecer limpeza dos filtros");
assert.match(app, /class="selection-actions financial-history-actions"/, "ações do histórico financeiro devem ficar no topo");
assert.match(app, /financial-history-actions[\s\S]*Estornar[\s\S]*Devolver valor[\s\S]*Gerar recibo/, "ações dos recebimentos devem manter a ordem solicitada no topo");
assert.match(app, /const history = renderActionTable\(dados, columns, \(\) => "", \{[\s\S]*filters: false,[\s\S]*selectableRows: true/, "histórico individual não deve exibir pesquisa nem coluna de ações");
assert.match(app, /firstEffective[\s\S]*selectReportRow\(firstEffective\)/, "o primeiro lançamento efetivo deve ser selecionado automaticamente");
assert.match(modules, /\.financial-history table\s*{\s*font-size:\s*\.8rem/, "histórico financeiro deve usar fonte levemente menor");
assert.match(modules, /\.financial-history \[data-column-key="forma_pagamento"\][\s\S]*white-space:\s*nowrap/, "formas de pagamento devem permanecer na mesma linha");
assert.match(app, /data-cash-filter="inicio"/, "fluxo de caixa deve filtrar pela data inicial");
assert.match(app, /data-cash-filter="fim"/, "fluxo de caixa deve filtrar pela data final");
assert.match(app, /metric\("Resultado", dados\.resultado, "info"\)/, "resultado do caixa deve usar sempre o tom azul");
assert.doesNotMatch(app, /paginationControls\("cash-page"|data-action="cash-page"/, "fluxo de caixa não deve possuir paginação");
assert.match(app, /api\(`\$\{url\}\$\{separador\}\$\{periodo\}`\)/, "fluxo de caixa deve solicitar todas as movimentações do período");
assert.match(modules, /\.cash-flow table\s*{\s*font-size:\s*\.82rem/, "fluxo de caixa deve usar fonte levemente menor");
assert.match(modules, /\.cash-flow \[data-column-key="data"\][^}]+white-space:\s*nowrap/s, "data do fluxo de caixa deve permanecer na mesma linha");
assert.match(app, /class="dashboard-recent-table"/, "movimentações recentes devem possuir estilo próprio de tabela");
assert.match(modules, /\.dashboard-recent-table table\s*{\s*font-size:\s*\.82rem/, "tabela da visão financeira deve usar fonte levemente menor");
assert.match(modules, /\.cash-flow-row--in td\s*{\s*color:\s*var\(--color-success\)/, "entradas do caixa devem usar texto verde");
assert.match(modules, /\.cash-flow-row--out td\s*{\s*color:\s*var\(--color-danger\)/, "saídas do caixa devem usar texto vermelho");
const removedReaderTerms = new RegExp(["c[oó]digo", " de ", "barras|codigo_", "barras|canteen-", "sc", "an|canteen-bar", "code"].join(""), "i");
assert.doesNotMatch(app, removedReaderTerms, "a interface não deve manter referências ao leitor excluído");
assert.match(app, /placeholder="Digite o nome do produto"/, "a Cantina deve pesquisar produtos somente pelo nome");
assert.match(app, /<select id="canteen-product">\$\{productOptions\}<\/select>/, "produtos da Cantina devem abrir em uma lista como os residentes");
assert.match(app, /data-action="open-canteen-product-search"/, "produtos da Cantina devem possuir botão de pesquisa");
assert.match(app, /data-action="select-canteen-product"/, "a pesquisa deve permitir escolher um produto da lista");
assert.match(app, /id="product-price"[^>]*type="text"[^>]*data-mask="currency"[^>]*value="R\$ 0,00"/, "preço do produto deve iniciar com máscara financeira sem setas numéricas");
assert.match(app, /data\.valor = currencyValue\(data\.valor\)\.toFixed\(2\)/, "preço mascarado do produto deve ser enviado com os centavos corretos");
assert.match(app, /class="product-form-grid"[\s\S]*product-unit[\s\S]*product-price[\s\S]*product-price-date[\s\S]*product-stock[\s\S]*product-minimum[\s\S]*product-status/, "cadastro de produto deve agrupar os seis campos em uma grade");
assert.match(app, /id="product-expiration" name="data_validade" type="date"/, "cadastro do produto deve aceitar validade opcional para o estoque inicial");
assert.match(app, /Validade do lote \(opcional\)<\/label><input name="data_validade" type="date"/, "reabastecimento deve aceitar a validade opcional do lote");
assert.match(modules, /\.product-form-grid\s*{[^}]*grid-template-columns:\s*repeat\(3,/s, "cadastro de produto deve exibir três campos por linha");
assert.doesNotMatch(app, /Unidades em estoque/, "produtos não devem exibir a soma de unidades de naturezas diferentes");
assert.match(app, /Produtos vencendo \(30 dias\)/, "produtos devem indicar vencimentos nos próximos 30 dias");
assert.match(app, /dados\.filter\(\(row\) => row\.produto_vencendo\)\.length/, "o indicador deve contar somente produtos sinalizados pelo controle de lotes");
assert.match(modules, /\.products-summary\s*{[^}]*grid-template-columns:\s*repeat\(4,/s, "os quatro indicadores de produtos devem ocupar a largura disponível");
assert.match(modules, /\.wallet-summary\s*{[^}]*grid-template-columns:\s*minmax\(0, 2fr\)\s+minmax\(0, 1fr\)\s+minmax\(0, 1fr\)/s, "resumo da carteira deve usar 50%, 25% e 25% em uma linha");
assert.match(app, /wallet-selector[\s\S]*open-wallet-resident-search[\s\S]*button--success[\s\S]*Nova carteira/, "seleção, pesquisa e nova carteira devem ficar na mesma linha e na ordem solicitada");
assert.match(app, /wallet-status--active[\s\S]*wallet-status--inactive/, "situação da carteira deve distinguir ativo e inativo por cor");
assert.match(app, /dados\.creditos[\s\S]*\{ filters: false \}/, "créditos da carteira não devem exibir pesquisa própria");
assert.match(app, /dados\.compras[^\n]+\{ filters: false \}/, "compras da carteira não devem exibir pesquisa própria");
assert.match(components, /\.button--success\s*{[^}]*background:\s*var\(--color-success\)/s, "botão Nova carteira deve usar verde");
assert.match(app, /Devolver saldo[\s\S]*data-action="wallet-report"[^>]*>Gerar relatório</, "Gerar relatório deve ser o último botão das ações da carteira");
assert.match(app, /\/api\/carteiras\/relatorio\?id=/, "o relatório deve consultar todas as movimentações dos últimos 30 dias");
assert.match(app, /resident-document wallet-report/, "o relatório da Cantina deve usar o documento preparado para impressão A4");
assert.match(app, /Imprimir \/ salvar PDF/, "o usuário deve poder imprimir ou salvar o relatório em PDF");
for (const reportContent of ["Saldo atual da Cantina", "Movimentações no período", "Créditos e compras da Cantina"]) {
    assert.ok(app.includes(reportContent), `o relatório deve conter ${reportContent}`);
}
assert.match(app, /\["Tipo", "modalidade", shortInitial\]/, "internações devem exibir o tipo pela inicial");
assert.match(app, /<label for="internment-modality">Tipo de residência<\/label>/, "formulários de internação devem usar a nomenclatura Tipo");
assert.doesNotMatch(app, />Modalidade(?: de residência)?</, "a interface não deve exibir a nomenclatura antiga");
assert.match(app, /data-action="open-edit-convenio">Editar convênio/, "internações devem permitir editar convênios existentes");
assert.match(app, /class="selection-actions internment-actions"/, "ações de internação devem ter layout compacto próprio");
assert.doesNotMatch(app, /<span class="selection-actions__label">Internação selecionada<\/span>/, "a barra não deve ocupar espaço com a indicação de seleção");
assert.match(modules, /\.selection-scope \.selection-actions\.internment-actions\s*\{[^}]*flex-wrap:\s*nowrap/s, "ações de internação devem permanecer em uma linha");
assert.doesNotMatch(app, /\["Cobrança", "tipo_cobranca_convenio"/, "internações não devem exibir a coluna Cobrança");
const internmentActions = app.match(/const actions = `<div class="selection-actions internment-actions"[^;]+;/)?.[0] || '';
for (const [left, right] of [["Nova internação", "Editar"], ["Editar", "Encerrar"], ["Encerrar", "Cancelar"], ["Cancelar", "Novo convênio"], ["Novo convênio", "Editar convênio"]]) {
    assert.ok(internmentActions.indexOf(left) < internmentActions.indexOf(right), `${left} deve aparecer antes de ${right}`);
}
assert.doesNotMatch(internmentActions, /Prorrogar|internment-extend/, "a barra de internações não deve exibir Prorrogar");
assert.match(modules, /\.internments-report table\s*{\s*font-size:\s*calc\(1em - 2\.5pt\)/, "tabela de internações deve usar fonte levemente menor");
assert.match(app, /data-endpoint="\/api\/convenios\/editar"/, "o formulário deve enviar a edição do convênio");
assert.match(tableLayout, /padding-top:\s*5px/, "painéis financeiros devem iniciar até 5 px abaixo do cabeçalho");
assert.match(tableLayout, /justify-content:\s*space-between/, "ações e limpeza devem ocupar a mesma linha");
assert.match(tableLayoutScript, /filters\.after\(toolbar\)/, "as ações devem ficar abaixo dos filtros");
assert.match(tableLayoutScript, /internmentActions \|\| toolbar\)\.append\(clear\)/, "Limpar filtros deve integrar a linha de ações das internações");
assert.match(auth, /\.settlement-form\s+\.login-error:empty\s*{[^}]*display:\s*none/s, "o formulário financeiro não deve reservar espaço para erro vazio");
for (const tone of ["particular", "convenio", "social", "voluntario"]) {
    assert.match(components, new RegExp(`\\.residence-type--${tone}`), `deve existir a cor do tipo ${tone}`);
}
assert.doesNotMatch(components.match(/\.residence-type\s*{[^}]*}/s)?.[0] || "", /background|border-radius|width|height/, "o tipo deve colorir somente a letra");
assert.match(components, /\.residence-type--voluntario\s*{\s*color:\s*#7e22ce;/, "voluntário deve usar letra roxa");

const typeHtml = renderActionTable(
    [
        { modalidade: "PARTICULAR" }, { modalidade: "CONVENIO" },
        { modalidade: "SOCIAL" }, { modalidade: "VOLUNTARIO" },
    ],
    [["Tipo", "modalidade", value => value.slice(0, 1)]],
    () => "",
);
for (const [tone, letter] of [["particular", "P"], ["convenio", "C"], ["social", "S"], ["voluntario", "V"]]) {
    assert.match(typeHtml, new RegExp(`residence-type--${tone}[^>]*>${letter}<`));
}

const html = renderActionTable(
    [{ nome: "Conta", status: "VENCIDA", valor: 12550 }],
    [["Nome", "nome"], ["Situação", "status"], ["Valor", "valor"]],
    () => '<button type="button">Abrir</button>',
);
assert.match(html, /status--danger/);
assert.match(html, /data-column-type="money"/);
assert.match(html, /data-column-key="status"/);
assert.match(html, /clear-table-filters/);

const selectable = renderActionTable(
    [{ id: 7, descricao: "Energia", status: "ABERTA" }],
    [["Descrição", "descricao"], ["Status", "status"]],
    () => '<button type="button">Pagar</button>',
    { selectableRows: true, selectionData: (row) => ({ id: row.id, capabilities: ["pay", "history"] }) },
);
assert.match(selectable, /data-action="select-report-row"/);
assert.match(selectable, /data-capabilities="pay history"/);
assert.doesNotMatch(selectable, /<th>Ações<\/th>/);

const cashRows = renderTable(
    [{ tipo: "ENTRADA", valor: 100 }, { tipo: "SAIDA", valor: 50 }],
    [["Tipo", "tipo"], ["Valor", "valor"]],
    { rowClass: row => `cash-flow-row--${row.tipo === "SAIDA" ? "out" : "in"}` },
);
assert.match(cashRows, /<tr class="cash-flow-row--in">/);
assert.match(cashRows, /<tr class="cash-flow-row--out">/);

console.log("Layout fluido, status, valores e controles das tabelas validados.");

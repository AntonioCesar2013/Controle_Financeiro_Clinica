(() => {
    "use strict";

    const app = document.querySelector("#app");
    const layers = {};
    let panelSequence = 0;

    const panels = {
        dashboard: ["Dashboard", "Visão gerencial", renderDashboard],
        financeiro: ["Financeiro", "Operações financeiras", renderDashboard],
        contas_receber: ["Contas a receber", "Financeiro", renderReceivables],
        contas_pagar: ["Contas a pagar", "Financeiro", renderPayables],
        caixa: ["Fluxo de caixa", "Financeiro", renderCashFlow],
        despesas: ["Despesas", "Financeiro", () => renderResource("/api/despesas", [
            ["Descrição", "descricao"], ["Setor", "setor_nome"], ["Tipo", "tipo_despesa_nome"], ["Natureza", "natureza"], ["Situação", "ativo", formatActive],
        ])],
        residentes: ["Residentes", "Cadastro e consulta", renderResidents],
        responsaveis: ["Responsáveis", "Cadastro e consulta", () => renderResource("/api/responsaveis", [
            ["Nome", "nome"], ["CPF", "cpf", formatCpf], ["Telefone", "telefone"], ["E-mail", "email"], ["Situação", "ativo", formatActive],
        ])],
        internacoes: ["Internações", "Acompanhamento", () => renderResource("/api/internacoes", [
            ["Residente", "residente_nome"], ["Responsável", "responsavel_nome"], ["Acolhimento", "data_acolhimento", formatDate], ["Período", "periodo_tratamento"], ["Contrato", "valor_contrato", formatMoney], ["Status", "status"],
        ])],
        carteiras: ["Carteiras", "Residentes", () => renderResource("/api/carteiras", [
            ["Residente", "residente_nome"], ["Saldo", "saldo", formatReais], ["Movimentações", "quantidade_movimentacoes"], ["Última movimentação", "ultima_movimentacao", formatDate], ["Situação", "ativo", formatActive],
        ])],
        itens: ["Itens", "Catálogo e valores", () => renderResource("/api/itens", [
            ["Código", "id"], ["Nome", "nome"], ["Situação", "ativo", formatActive],
        ])],
        colaboradores: ["Colaboradores", "Acesso e equipe", () => renderResource("/api/colaboradores", [
            ["Nome", "nome"], ["CPF", "cpf", formatCpf], ["Status", "status"], ["Criado em", "criado_em", formatDateTime],
        ])],
        relatorios: ["Relatórios", "Análise por período", renderReports],
        configuracoes: ["Configurações", "Preferências do sistema", renderSettings],
    };

    function initialize() {
        app.innerHTML = `
            <div class="panel-layer panel-layer--main" data-layer="main"></div>
            <div class="panel-layer panel-layer--menu" data-layer="menu"></div>
            <div class="panel-layer panel-layer--auxiliary" data-layer="auxiliary"></div>
            <div class="panel-layer panel-layer--modal" data-layer="modal"></div>
            <div class="panel-layer panel-layer--auth" data-layer="auth"></div>
        `;
        app.querySelectorAll("[data-layer]").forEach((layer) => { layers[layer.dataset.layer] = layer; });
        app.addEventListener("click", handleClick);
        app.addEventListener("submit", handleSubmit);
        app.addEventListener("pointerdown", (event) => {
            const panel = event.target.closest(".panel");
            if (panel) panel.style.zIndex = String(++panelSequence);
        });
        document.addEventListener("keydown", handleKeydown);
        checkAccess();
    }

    async function api(url, options = {}) {
        const response = await fetch(url, {
            method: options.method || "GET",
            headers: options.body ? { "Content-Type": "application/json" } : {},
            body: options.body ? JSON.stringify(options.body) : undefined,
            credentials: "same-origin",
        });
        const payload = await response.json().catch(() => ({}));
        if (response.status === 401 && !options.allowUnauthorized) {
            showLogin(false, "Sua sessão expirou. Entre novamente.");
            throw new Error("Sessão expirada.");
        }
        if (!response.ok) throw new Error(payload.erro || "Não foi possível concluir a operação.");
        return payload;
    }

    async function checkAccess() {
        try {
            const status = await api("/api/auth/status", { allowUnauthorized: true });
            if (status.autenticado) openGeneralMenu();
            else showLogin(!status.configurado);
        } catch (_) {
            showConnectionError();
        }
    }

    function handleClick(event) {
        const trigger = event.target.closest("[data-action]");
        if (!trigger) return;
        const { action, panel } = trigger.dataset;
        if (action === "open-panel") openMainPanel(panel);
        if (action === "open-financial-menu") openFinancialMenu();
        if (action === "open-general-menu") openGeneralMenu();
        if (action === "close-panel") closePanel(trigger.closest(".panel"));
        if (action === "open-new-resident") openResidentForm();
        if (action === "toggle-password") togglePassword(trigger);
        if (action === "logout") logout();
        if (action === "apply-report") refreshReport(trigger.closest(".panel"));
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (event.target.matches("#login-form")) return submitLogin(event.target);
        if (event.target.matches("#setup-form")) return submitSetup(event.target);
        if (event.target.matches("#resident-form")) return submitResident(event.target);
    }

    function handleKeydown(event) {
        if (layers.auth.children.length || event.key !== "Escape") return;
        if (layers.modal.children.length) closeLayer("modal");
        else if (layers.auxiliary.children.length) closeLayer("auxiliary");
        else if (layers.main.children.length) closeLayer("main");
    }

    function showLogin(firstAccess = false, message = "") {
        ["main", "menu", "auxiliary", "modal"].forEach((name) => closeLayer(name, false));
        const fields = firstAccess
            ? '<div class="field"><label for="setup-name">Nome</label><input id="setup-name" name="nome" autocomplete="name" required></div><div class="field"><label for="login-user">CPF</label><input id="login-user" name="cpf" inputmode="numeric" autocomplete="username" required></div>'
            : '<div class="field"><label for="login-user">CPF</label><input id="login-user" name="cpf" inputmode="numeric" autocomplete="username" required></div>';
        layers.auth.innerHTML = `
            <div class="login-backdrop"><section class="login-panel" aria-labelledby="login-title">
                <div class="login-panel__brand"><span class="login-panel__mark" aria-hidden="true">CF</span><div><strong>Controle Financeiro</strong><span>Clínica de recuperação</span></div></div>
                <h1 id="login-title">${firstAccess ? "Configurar primeiro acesso" : "Acessar o sistema"}</h1>
                <p class="login-panel__intro">${firstAccess ? "Cadastre o primeiro colaborador administrador." : "Informe suas credenciais para entrar."}</p>
                <form class="login-form" id="${firstAccess ? "setup-form" : "login-form"}">
                    ${fields}
                    <div class="field login-password"><label for="login-password">Senha</label><input id="login-password" name="senha" type="password" minlength="8" autocomplete="${firstAccess ? "new-password" : "current-password"}" required><button class="login-password__toggle" type="button" data-action="toggle-password">Mostrar</button></div>
                    <p class="login-error" id="login-error" role="alert" aria-live="polite">${escapeHtml(message)}</p>
                    <button class="button" type="submit">${firstAccess ? "Criar acesso" : "Entrar"}</button>
                </form>
            </section></div>`;
        requestAnimationFrame(() => layers.auth.querySelector("input")?.focus());
    }

    function showConnectionError() {
        layers.auth.innerHTML = '<div class="login-backdrop"><section class="login-panel"><h1>Servidor não iniciado</h1><p class="login-panel__intro">Abra o sistema pelo endereço fornecido pelo servidor Python. O arquivo HTML isolado não consegue acessar o backend.</p><p class="login-panel__note"><strong>Execute:</strong> python -m src.servidor<br><strong>Acesse:</strong> http://127.0.0.1:8000</p></section></div>';
    }

    async function submitLogin(form) {
        setFormBusy(form, true);
        try {
            await api("/api/auth/login", { method: "POST", body: Object.fromEntries(new FormData(form)) });
            layers.auth.replaceChildren();
            openGeneralMenu();
        } catch (error) { form.querySelector("#login-error").textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function submitSetup(form) {
        setFormBusy(form, true);
        try {
            await api("/api/auth/setup", { method: "POST", body: Object.fromEntries(new FormData(form)), allowUnauthorized: true });
            showLogin(false, "Acesso criado. Entre com o CPF e a senha cadastrados.");
        } catch (error) { form.querySelector("#login-error").textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    function togglePassword(trigger) {
        const input = layers.auth.querySelector("#login-password");
        if (!input) return;
        input.type = input.type === "password" ? "text" : "password";
        trigger.textContent = input.type === "password" ? "Mostrar" : "Ocultar";
    }

    async function logout() {
        try { await api("/api/auth/logout", { method: "POST" }); } catch (_) { /* sessão já encerrada */ }
        showLogin(false);
    }

    function openGeneralMenu() {
        renderMenu("Menu geral", "Controle Financeiro", [
            ["dashboard", "Dashboard", "Indicadores e movimentos", "open-panel"],
            ["relatorios", "Relatórios", "Análises por período", "open-panel"],
            ["financeiro", "Financeiro", "Receber, pagar e caixa", "open-financial-menu"],
            ["carteiras", "Carteiras", "Saldos por residente", "open-panel"],
            ["internacoes", "Internações", "Acolhimentos e contratos", "open-panel"],
            ["residentes", "Residentes", "Cadastro e consulta", "open-panel"],
            ["responsaveis", "Responsáveis", "Contatos e vínculos", "open-panel"],
            ["colaboradores", "Colaboradores", "Equipe e acessos", "open-panel"],
            ["itens", "Itens", "Catálogo e valores", "open-panel"],
            ["configuracoes", "Configurações", "Parâmetros do sistema", "open-panel"],
            ["", "Sair", "Encerrar esta sessão", "logout"],
        ]);
    }

    function openFinancialMenu() {
        renderMenu("Menu financeiro", "Módulo", [
            ["financeiro", "Visão financeira", "Resumo do módulo", "open-panel"],
            ["contas_receber", "Contas a receber", "Cobranças e recebimentos", "open-panel"],
            ["contas_pagar", "Contas a pagar", "Vencimentos e pagamentos", "open-panel"],
            ["caixa", "Fluxo de caixa", "Entradas, saídas e resultado", "open-panel"],
            ["despesas", "Despesas", "Setores e classificações", "open-panel"],
            ["", "Sair", "Encerrar esta sessão", "logout"],
        ], true);
        openMainPanel("financeiro");
    }

    function renderMenu(title, eyebrow, items, back = false) {
        const body = `<div class="menu-context">${back ? '<button class="menu-context__back" type="button" data-action="open-general-menu">← Menu geral</button>' : ""}<nav class="menu-grid" aria-label="${title}">${items.map(([id, label, description, action]) => `<button class="menu-item" type="button" data-action="${action}"${id ? ` data-panel="${id}"` : ""}><strong>${label}</strong><span>${description}</span></button>`).join("")}</nav></div>`;
        layers.menu.replaceChildren(createPanel({ id: back ? "financial-menu" : "general-menu", title, eyebrow, body, size: "menu", closable: false }));
    }

    async function openMainPanel(name) {
        const definition = panels[name];
        if (!definition) return;
        closeLayer("auxiliary", false);
        closeLayer("modal", false);
        closeLayer("main", false);
        const [title, eyebrow, renderer] = definition;
        layers.main.append(createPanel({ id: `panel-${name}`, title, eyebrow, body: loadingState() }));
        const panel = layers.main.querySelector(".panel");
        try { panel.querySelector(".panel__body").innerHTML = await renderer(); }
        catch (error) { panel.querySelector(".panel__body").innerHTML = errorState(error.message); }
    }

    function createPanel({ id = `panel-${++panelSequence}`, title, eyebrow, body, footer = "", size = "large", modal = false, closable = true }) {
        const wrapper = document.createElement("div");
        wrapper.innerHTML = `${modal ? '<div class="panel-backdrop panel-backdrop--modal"></div>' : ""}<section class="panel panel--${size}" id="${id}" role="${modal ? "alertdialog" : "dialog"}" aria-labelledby="${id}-title" tabindex="-1"><header class="panel__header"><div class="panel__heading">${eyebrow ? `<p class="panel__eyebrow">${eyebrow}</p>` : ""}<h2 class="panel__title" id="${id}-title">${title}</h2></div>${closable ? `<button class="panel__close" type="button" data-action="close-panel" aria-label="Fechar ${title}">&times;</button>` : ""}</header><div class="panel__body">${body}</div>${footer ? `<footer class="panel__footer">${footer}</footer>` : ""}</section>`;
        const fragment = document.createDocumentFragment();
        while (wrapper.firstChild) fragment.append(wrapper.firstChild);
        return fragment;
    }

    function closePanel(panel) { if (panel) panel.parentElement.replaceChildren(); }
    function closeLayer(name) { if (layers[name]) layers[name].replaceChildren(); }

    function showAlert(title, message) {
        layers.modal.replaceChildren(createPanel({ title, body: `<div class="modal-message"><span class="modal-message__icon">i</span><p>${escapeHtml(message)}</p></div>`, footer: '<button class="button" type="button" data-action="close-panel">OK</button>', size: "small", modal: true }));
    }

    function openResidentForm() {
        const body = '<form class="login-form" id="resident-form"><div class="field"><label for="resident-name">Nome</label><input id="resident-name" name="nome" required></div><div class="field"><label for="resident-cpf">CPF</label><input id="resident-cpf" name="cpf" inputmode="numeric" required></div><div class="field"><label for="resident-city">Cidade de origem</label><input id="resident-city" name="cidade_origem"></div><p class="login-error" id="resident-error" role="alert"></p><button class="button" type="submit">Salvar residente</button></form>';
        layers.auxiliary.replaceChildren(createPanel({ title: "Novo residente", eyebrow: "Cadastro", body, size: "medium" }));
    }

    async function submitResident(form) {
        setFormBusy(form, true);
        try {
            await api("/api/residentes", { method: "POST", body: Object.fromEntries(new FormData(form)) });
            closeLayer("auxiliary");
            await openMainPanel("residentes");
            showAlert("Residente salvo", "O cadastro foi registrado com sucesso.");
        } catch (error) { form.querySelector("#resident-error").textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function renderDashboard() {
        const { dados } = await api("/api/dashboard");
        return `<div class="metrics">${metric("Entradas do mês", dados.total_entradas, "success")}${metric("Saídas do mês", dados.total_saidas, "danger")}${metric("Resultado", dados.resultado, "primary")}${metric("A receber", dados.total_receber, "warning")}${metric("A pagar", dados.total_pagar, "warning")}</div><h3 class="section-title">Movimentações recentes</h3>${renderTable(dados.movimentacoes_recentes, [["Data", "data", formatDate], ["Descrição", "descricao"], ["Tipo", "tipo"], ["Forma", "forma_pagamento"], ["Valor", "valor", formatMoney]])}`;
    }

    async function renderResidents() {
        const { dados } = await api("/api/residentes");
        return `<div class="toolbar"><div></div><button class="button" type="button" data-action="open-new-resident">Novo residente</button></div>${renderTable(dados, [["Nome", "nome"], ["CPF", "cpf", formatCpf], ["Cidade de origem", "cidade_origem"], ["Situação", "ativo", formatActive]])}`;
    }

    async function renderReceivables() {
        return renderResource("/api/contas-receber", [["Internação", "internacao_id"], ["Parcela", "numero_parcela"], ["Tipo", "tipo"], ["Vencimento", "data_vencimento", formatDate], ["Valor devido", "valor_devido", formatMoney], ["Recebido", "total_recebido", formatMoney], ["Saldo", "saldo_restante", formatMoney], ["Situação", "situacao_temporal", valueOrStatus]]);
    }

    async function renderPayables() {
        return renderResource("/api/contas-pagar", [["Descrição", "despesa_descricao"], ["Setor", "setor_nome"], ["Tipo", "tipo_despesa_nome"], ["Vencimento", "data_vencimento", formatDate], ["Valor", "valor", formatMoney], ["Status", "status"]]);
    }

    async function renderCashFlow(url = "/api/caixa") {
        const { dados } = await api(url);
        return `<div class="metrics">${metric("Entradas", dados.total_entradas, "success")}${metric("Saídas", dados.total_saidas, "danger")}${metric("Resultado", dados.resultado, "primary")}</div>${renderTable(dados.movimentacoes, [["Data", "data", formatDate], ["Descrição", "descricao"], ["Tipo", "tipo"], ["Forma", "forma_pagamento"], ["Valor", "valor", formatMoney]])}`;
    }

    async function renderReports() {
        const today = new Date().toISOString().slice(0, 10);
        const start = `${today.slice(0, 8)}01`;
        return `<div class="toolbar"><div class="toolbar__group"><div class="field"><label for="report-start">Data inicial</label><input id="report-start" type="date" value="${start}"></div><div class="field"><label for="report-end">Data final</label><input id="report-end" type="date" value="${today}"></div></div><button class="button" type="button" data-action="apply-report">Consultar</button></div><div data-report-results>${await renderCashFlow(`/api/caixa?data_inicio=${start}&data_fim=${today}`)}</div>`;
    }

    async function refreshReport(panel) {
        const start = panel.querySelector("#report-start").value;
        const end = panel.querySelector("#report-end").value;
        const target = panel.querySelector("[data-report-results]");
        target.innerHTML = loadingState();
        try { target.innerHTML = await renderCashFlow(`/api/caixa?data_inicio=${encodeURIComponent(start)}&data_fim=${encodeURIComponent(end)}`); }
        catch (error) { target.innerHTML = errorState(error.message); }
    }

    async function renderSettings() {
        const { dados } = await api("/api/configuracoes");
        if (!dados) return emptyState();
        return renderTable([dados], [["Aplicar juros", "aplicar_juros", formatYesNo], ["Tipo de juros", "tipo_juros"], ["Valor dos juros", "valor_juros"], ["Aplicar multa", "aplicar_multa", formatYesNo], ["Tipo da multa", "tipo_multa"], ["Valor da multa", "valor_multa"]]);
    }

    async function renderResource(url, columns) {
        const { dados } = await api(url);
        return renderTable(dados, columns);
    }

    function renderTable(rows, columns) {
        if (!rows?.length) return emptyState();
        return `<div class="table-wrap"><table><thead><tr>${columns.map(([label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${columns.map(([, key, formatter]) => `<td>${escapeHtml(formatter ? formatter(row[key], row) : valueOrDash(row[key]))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    }

    function metric(label, value, tone) { return `<article class="metric metric--${tone}"><span class="metric__label">${label}</span><strong class="metric__value">${formatMoney(value)}</strong></article>`; }
    function loadingState() { return '<div class="placeholder"><div><h3>Carregando</h3><p>Consultando dados do sistema…</p></div></div>'; }
    function emptyState() { return '<div class="placeholder"><div><h3>Nenhum registro encontrado</h3><p>Não há dados cadastrados para esta consulta.</p></div></div>'; }
    function errorState(message) { return `<div class="placeholder"><div><h3>Não foi possível carregar</h3><p>${escapeHtml(message)}</p></div></div>`; }
    function setFormBusy(form, busy) { form.querySelectorAll("input, button, select").forEach((element) => { element.disabled = busy; }); }
    function formatMoney(value) { return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value || 0) / 100); }
    function formatReais(value) { return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value || 0)); }
    function formatDate(value) { if (!value) return "—"; const [year, month, day] = String(value).slice(0, 10).split("-"); return year && month && day ? `${day}/${month}/${year}` : String(value); }
    function formatDateTime(value) { return value ? `${formatDate(value)} ${String(value).slice(11, 16)}`.trim() : "—"; }
    function formatCpf(value) { const digits = String(value || "").replace(/\D/g, ""); return digits.length === 11 ? digits.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4") : valueOrDash(value); }
    function formatActive(value) { return Number(value) === 1 ? "Ativo" : "Inativo"; }
    function formatYesNo(value) { return Number(value) === 1 ? "Sim" : "Não"; }
    function valueOrStatus(value, row) { return valueOrDash(value || row.status); }
    function valueOrDash(value) { return value === null || value === undefined || value === "" ? "—" : String(value); }
    function escapeHtml(value) { return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]); }

    initialize();
})();

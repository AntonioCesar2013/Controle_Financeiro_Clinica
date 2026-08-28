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
        responsaveis: ["Responsáveis", "Cadastro e consulta", renderGuardians],
        internacoes: ["Internações", "Acompanhamento", renderInternments],
        carteiras: ["Carteiras", "Saldo e compras dos residentes", renderWallets],
        cantina: ["Cantina", "Mercadinho dos residentes", renderCantina],
        itens: ["Produtos da Cantina", "Catálogo, preços e estoque", renderProducts],
        colaboradores: ["Colaboradores", "Acesso e equipe", renderCollaborators],
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
        app.addEventListener("change", handleChange);
        app.addEventListener("pointerdown", (event) => {
            const panel = event.target.closest(".panel");
            if (panel) panel.style.zIndex = String(++panelSequence);
        });
        document.addEventListener("keydown", handleKeydown);
        // TESTES: reative esta linha para tornar o login obrigatório novamente.
        // checkAccess();
        openGeneralMenu();
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
        if (response.status === 404 && payload.erro === "Rota não encontrada.") {
            throw new Error("O servidor está executando uma versão anterior. Encerre o Python e inicie o sistema novamente.");
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
        if (action === "open-new-collaborator") openCollaboratorForm();
        if (action === "open-new-product") openProductForm();
        if (action === "open-new-guardian") openGuardianForm();
        if (action === "open-new-internment") openInternmentForm();
        if (action === "toggle-password") togglePassword(trigger);
        if (action === "logout") logout();
        if (action === "apply-report") refreshReport(trigger.closest(".panel"));
        if (action === "print-report") window.print();
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (event.target.matches("#login-form")) return submitLogin(event.target);
        if (event.target.matches("#setup-form")) return submitSetup(event.target);
        if (event.target.matches("#resident-form")) return submitResident(event.target);
        if (event.target.matches("#collaborator-form")) return submitCollaborator(event.target);
        if (event.target.matches("#canteen-sale-form")) return submitCanteenSale(event.target);
        if (event.target.matches("#product-form")) return submitProduct(event.target);
        if (event.target.matches("#guardian-form")) return submitGuardian(event.target);
        if (event.target.matches("#internment-form")) return submitInternment(event.target);
    }

    function handleChange(event) {
        if (event.target.matches("#wallet-resident")) refreshWalletDetail(event.target);
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
        const passwordConfirmation = firstAccess
            ? '<div class="field login-password"><label for="login-password-confirmation">Confirmar senha</label><input id="login-password-confirmation" name="confirmacao_senha" type="password" minlength="8" autocomplete="new-password" required><button class="login-password__toggle" type="button" data-action="toggle-password" aria-controls="login-password-confirmation">Mostrar</button></div>'
            : "";
        layers.auth.innerHTML = `
            <div class="login-backdrop"><section class="login-panel" aria-labelledby="login-title">
                <div class="login-panel__brand"><span class="login-panel__mark" aria-hidden="true">CF</span><div><strong>Controle Financeiro</strong><span>Clínica de recuperação</span></div></div>
                <h1 id="login-title">${firstAccess ? "Configurar primeiro acesso" : "Acessar o sistema"}</h1>
                <p class="login-panel__intro">${firstAccess ? "Cadastre o primeiro colaborador administrador." : "Informe suas credenciais para entrar."}</p>
                <form class="login-form" id="${firstAccess ? "setup-form" : "login-form"}">
                    ${fields}
                    <div class="field login-password"><label for="login-password">Senha</label><input id="login-password" name="senha" type="password" minlength="8" autocomplete="${firstAccess ? "new-password" : "current-password"}" required><button class="login-password__toggle" type="button" data-action="toggle-password" aria-controls="login-password">Mostrar</button></div>
                    ${passwordConfirmation}
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
        const data = Object.fromEntries(new FormData(form));
        setFormBusy(form, true);
        try {
            await api("/api/auth/login", { method: "POST", body: data });
            layers.auth.replaceChildren();
            openGeneralMenu();
        } catch (error) { form.querySelector("#login-error").textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function submitSetup(form) {
        const data = Object.fromEntries(new FormData(form));
        if (data.senha !== data.confirmacao_senha) {
            form.querySelector("#login-error").textContent = "A confirmação da senha não confere.";
            form.elements.confirmacao_senha.focus();
            return;
        }
        delete data.confirmacao_senha;
        setFormBusy(form, true);
        try {
            await api("/api/auth/setup", { method: "POST", body: data, allowUnauthorized: true });
            showLogin(false, "Acesso criado. Entre com o CPF e a senha cadastrados.");
        } catch (error) { form.querySelector("#login-error").textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    function togglePassword(trigger) {
        const inputId = trigger.getAttribute("aria-controls");
        const input = inputId ? document.getElementById(inputId) : null;
        if (!input) return;
        input.type = input.type === "password" ? "text" : "password";
        trigger.textContent = input.type === "password" ? "Mostrar" : "Ocultar";
    }

    async function logout() {
        try { await api("/api/auth/logout", { method: "POST" }); } catch (_) { /* sessão já encerrada */ }
        // TESTES: reative esta linha para voltar à tela de login ao sair.
        // showLogin(false);
        openGeneralMenu();
    }

    function openGeneralMenu() {
        renderMenu("Menu geral", "Controle Financeiro", [
            ["dashboard", "Dashboard", "Indicadores e movimentos", "open-panel"],
            ["relatorios", "Relatórios", "Análises por período", "open-panel"],
            ["financeiro", "Financeiro", "Receber, pagar e caixa", "open-financial-menu"],
            ["carteiras", "Carteiras", "Saldos por residente", "open-panel"],
            ["cantina", "Cantina", "Mercadinho dos residentes", "open-panel"],
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

    function openCollaboratorForm() {
        const body = `
            <form class="login-form" id="collaborator-form">
                <div class="field"><label for="collaborator-name">Nome</label><input id="collaborator-name" name="nome" autocomplete="name" required></div>
                <div class="field"><label for="collaborator-cpf">CPF</label><input id="collaborator-cpf" name="cpf" inputmode="numeric" autocomplete="off" placeholder="Somente números" required></div>
                <div class="field"><label for="collaborator-status">Status</label><select id="collaborator-status" name="status" required><option value="ATIVO">Ativo</option><option value="INATIVO">Inativo</option></select></div>
                <div class="field login-password"><label for="collaborator-password">Senha</label><input id="collaborator-password" name="senha" type="password" minlength="8" autocomplete="new-password" required><button class="login-password__toggle" type="button" data-action="toggle-password" aria-controls="collaborator-password">Mostrar</button></div>
                <div class="field login-password"><label for="collaborator-password-confirmation">Confirmar senha</label><input id="collaborator-password-confirmation" name="confirmacao_senha" type="password" minlength="8" autocomplete="new-password" required><button class="login-password__toggle" type="button" data-action="toggle-password" aria-controls="collaborator-password-confirmation">Mostrar</button></div>
                <p class="login-error" id="collaborator-error" role="alert" aria-live="polite"></p>
                <button class="button" type="submit">Salvar colaborador</button>
            </form>`;
        layers.auxiliary.replaceChildren(createPanel({ title: "Novo colaborador", eyebrow: "Cadastro e acesso", body, size: "medium" }));
        requestAnimationFrame(() => document.getElementById("collaborator-name")?.focus());
    }

    function openProductForm() {
        const today = new Date().toISOString().slice(0, 10);
        const body = `<form class="login-form" id="product-form">
            <div class="field"><label for="product-name">Nome do produto</label><input id="product-name" name="nome" required></div>
            <div class="field"><label for="product-barcode">Código de barras</label><input id="product-barcode" name="codigo_barras" inputmode="numeric"></div>
            <div class="field"><label for="product-category">Categoria</label><input id="product-category" name="categoria" placeholder="Ex.: Bebidas, doces, higiene"></div>
            <div class="field"><label for="product-description">Descrição</label><textarea id="product-description" name="descricao" rows="3"></textarea></div>
            <div class="field"><label for="product-unit">Unidade</label><select id="product-unit" name="unidade_medida" required><option value="UN">Unidade</option><option value="PCT">Pacote</option><option value="CX">Caixa</option><option value="KG">Quilograma</option><option value="L">Litro</option></select></div>
            <div class="field"><label for="product-price">Preço de venda</label><input id="product-price" name="valor" type="number" min="0.01" step="0.01" required></div>
            <div class="field"><label for="product-price-date">Preço válido desde</label><input id="product-price-date" name="data_inicio_valor" type="date" value="${today}" required></div>
            <div class="field"><label for="product-stock">Estoque inicial</label><input id="product-stock" name="estoque_inicial" type="number" min="0" step="1" value="0" required></div>
            <div class="field"><label for="product-minimum">Estoque mínimo</label><input id="product-minimum" name="estoque_minimo" type="number" min="0" step="1" value="0" required></div>
            <div class="field"><label for="product-status">Status</label><select id="product-status" name="ativo"><option value="1">Ativo</option><option value="0">Inativo</option></select></div>
            <p class="login-error" data-product-error role="alert"></p><button class="button" type="submit">Salvar produto</button>
        </form>`;
        layers.auxiliary.replaceChildren(createPanel({ title: "Novo produto", eyebrow: "Cantina", body, size: "medium" }));
        requestAnimationFrame(() => document.getElementById("product-name")?.focus());
    }

    function openGuardianForm() {
        const body = `<form class="login-form" id="guardian-form"><div class="field"><label for="guardian-name">Nome</label><input id="guardian-name" name="nome" required></div><div class="field"><label for="guardian-cpf">CPF</label><input id="guardian-cpf" name="cpf" inputmode="numeric" placeholder="Somente números" required></div><div class="field"><label for="guardian-phone">Telefone</label><input id="guardian-phone" name="telefone" type="tel"></div><div class="field"><label for="guardian-email">E-mail</label><input id="guardian-email" name="email" type="email"></div><p class="login-error" data-guardian-error role="alert"></p><button class="button" type="submit">Salvar responsável</button></form>`;
        layers.auxiliary.replaceChildren(createPanel({ title: "Novo responsável", eyebrow: "Cadastro", body, size: "medium" }));
        requestAnimationFrame(() => document.getElementById("guardian-name")?.focus());
    }

    async function openInternmentForm() {
        try {
            const [residentsResponse, guardiansResponse] = await Promise.all([api("/api/residentes"), api("/api/responsaveis")]);
            const residents = residentsResponse.dados || [];
            const guardians = guardiansResponse.dados || [];
            if (!residents.length || !guardians.length) {
                showAlert("Cadastro necessário", "Cadastre pelo menos um residente e um responsável antes de criar a internação.");
                return;
            }
            const residentOptions = residents.map((item) => `<option value="${item.id}">${escapeHtml(item.nome)}</option>`).join("");
            const guardianOptions = guardians.map((item) => `<option value="${item.id}">${escapeHtml(item.nome)}</option>`).join("");
            const today = new Date().toISOString().slice(0, 10);
            const body = `<form class="login-form" id="internment-form"><div class="field"><label for="internment-resident">Residente</label><select id="internment-resident" name="residente_id" required>${residentOptions}</select></div><div class="field"><label for="internment-guardian">Responsável</label><select id="internment-guardian" name="responsavel_id" required>${guardianOptions}</select></div><div class="field"><label for="internment-date">Data de acolhimento</label><input id="internment-date" name="data_acolhimento" type="date" value="${today}" required></div><div class="field"><label for="internment-period">Período de tratamento (meses)</label><input id="internment-period" name="periodo_tratamento" type="number" min="1" step="1" required></div><div class="field"><label for="internment-contract">Valor do contrato</label><input id="internment-contract" name="valor_contrato" type="number" min="0" step="0.01" value="0" required></div><div class="field"><label for="internment-welcome">Valor do acolhimento</label><input id="internment-welcome" name="valor_acolhimento" type="number" min="0" step="0.01" value="0" required></div><div class="field"><label for="internment-monthly">Mensalidade</label><input id="internment-monthly" name="valor_mensalidade" type="number" min="0" step="0.01" value="0" required></div><p class="form-note">O residente ficará ativo somente enquanto esta internação estiver dentro do período contratado.</p><p class="login-error" data-internment-error role="alert"></p><button class="button" type="submit">Salvar internação</button></form>`;
            layers.auxiliary.replaceChildren(createPanel({ title: "Nova internação", eyebrow: "Acolhimento e contrato", body, size: "medium" }));
        } catch (error) { showAlert("Não foi possível abrir", error.message); }
    }

    async function submitResident(form) {
        const data = Object.fromEntries(new FormData(form));
        setFormBusy(form, true);
        try {
            await api("/api/residentes", { method: "POST", body: data });
            closeLayer("auxiliary");
            await openMainPanel("residentes");
            showAlert("Residente salvo", "O cadastro foi registrado com sucesso.");
        } catch (error) { form.querySelector("#resident-error").textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function submitCollaborator(form) {
        const data = Object.fromEntries(new FormData(form));
        const errorElement = form.querySelector("#collaborator-error");
        if (data.senha !== data.confirmacao_senha) {
            errorElement.textContent = "A confirmação da senha não confere.";
            form.elements.confirmacao_senha.focus();
            return;
        }

        delete data.confirmacao_senha;
        setFormBusy(form, true);
        try {
            await api("/api/colaboradores", { method: "POST", body: data });
            closeLayer("auxiliary");
            await openMainPanel("colaboradores");
            showAlert("Colaborador salvo", "O colaborador e suas credenciais foram registrados com sucesso.");
        } catch (error) { errorElement.textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function submitCanteenSale(form) {
        const data = Object.fromEntries(new FormData(form));
        const errorElement = form.querySelector("[data-canteen-error]");
        setFormBusy(form, true);
        try {
            const resultado = await api("/api/cantina/vendas", { method: "POST", body: data });
            await openMainPanel("cantina");
            showAlert("Compra concluída", `${resultado.residente} comprou ${resultado.quantidade}x ${resultado.item}. Saldo atual: ${formatReais(resultado.saldo)}.`);
        } catch (error) { errorElement.textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function submitProduct(form) {
        const data = Object.fromEntries(new FormData(form));
        setFormBusy(form, true);
        try {
            await api("/api/itens", { method: "POST", body: data });
            closeLayer("auxiliary");
            await openMainPanel("itens");
            showAlert("Produto salvo", "O produto, o preço e o estoque foram cadastrados com sucesso.");
        } catch (error) { form.querySelector("[data-product-error]").textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function submitGuardian(form) {
        const data = Object.fromEntries(new FormData(form));
        setFormBusy(form, true);
        try {
            await api("/api/responsaveis", { method: "POST", body: data });
            closeLayer("auxiliary"); await openMainPanel("responsaveis");
            showAlert("Responsável salvo", "O responsável foi cadastrado com sucesso.");
        } catch (error) { form.querySelector("[data-guardian-error]").textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function submitInternment(form) {
        const data = Object.fromEntries(new FormData(form));
        setFormBusy(form, true);
        try {
            const resultado = await api("/api/internacoes", { method: "POST", body: data });
            closeLayer("auxiliary"); await openMainPanel("internacoes");
            showAlert("Internação salva", `A internação foi cadastrada e ${resultado.cobrancas || 0} cobranças foram geradas.`);
        } catch (error) { form.querySelector("[data-internment-error]").textContent = error.message; }
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

    async function renderGuardians() {
        const { dados } = await api("/api/responsaveis");
        return `<div class="toolbar"><div></div><button class="button" type="button" data-action="open-new-guardian">Novo responsável</button></div>${renderTable(dados, [["Nome", "nome"], ["CPF", "cpf", formatCpf], ["Telefone", "telefone"], ["E-mail", "email"], ["Situação", "ativo", formatActive]])}`;
    }

    async function renderInternments() {
        const { dados } = await api("/api/internacoes");
        return `<div class="toolbar"><div></div><button class="button" type="button" data-action="open-new-internment">Nova internação</button></div>${renderTable(dados, [["Residente", "residente_nome"], ["Responsável", "responsavel_nome"], ["Acolhimento", "data_acolhimento", formatDate], ["Período (meses)", "periodo_tratamento"], ["Contrato", "valor_contrato", formatMoney], ["Acolhimento", "valor_acolhimento", formatMoney], ["Mensalidade", "valor_mensalidade", formatMoney], ["Status", "status"]])}`;
    }

    async function renderWallets() {
        const { dados } = await api("/api/carteiras");
        if (!dados?.length) return emptyState("Nenhuma carteira cadastrada", "Crie uma carteira para o residente antes de consultar saldo e compras.");
        const options = dados.map((wallet) => `<option value="${wallet.id}">${escapeHtml(wallet.residente_nome)}</option>`).join("");
        const first = await renderWalletDetail(dados[0].id);
        return `<div class="wallet-selector"><div class="field"><label for="wallet-resident">Residente</label><select id="wallet-resident">${options}</select></div></div><div data-wallet-detail>${first}</div>`;
    }

    async function refreshWalletDetail(select) {
        const target = select.closest(".panel__body").querySelector("[data-wallet-detail]");
        target.innerHTML = loadingState();
        try { target.innerHTML = await renderWalletDetail(select.value); }
        catch (error) { target.innerHTML = errorState(error.message); }
    }

    async function renderWalletDetail(walletId) {
        const resultado = await api(`/api/carteiras/detalhe?id=${encodeURIComponent(walletId)}`);
        const dados = resultado.dados;
        if (!dados?.sucesso) throw new Error(dados?.erro || "Carteira não encontrada.");
        const wallet = dados.carteira;
        const purchases = renderTable(dados.compras, [["Data", "data_movimentacao", formatDate], ["Produto", "item_nome"], ["Quantidade", "quantidade"], ["Valor unitário", "valor_unitario", formatReais], ["Total descontado", "valor_total", formatReais]]);
        return `<div class="wallet-summary"><article><span>Residente</span><strong>${escapeHtml(wallet.residente_nome)}</strong></article><article><span>Saldo disponível</span><strong>${escapeHtml(formatReais(wallet.saldo))}</strong></article></div><h3 class="section-title">Histórico de compras na Cantina</h3>${purchases}`;
    }

    async function renderCantina() {
        const { dados } = await api("/api/cantina");
        const wallets = dados.carteiras || [];
        const products = dados.itens || [];
        if (!wallets.length || !products.length) {
            const missing = [!wallets.length ? "uma carteira ativa para o residente" : "", !products.length ? "itens ativos com preço vigente" : ""].filter(Boolean).join(" e ");
            return `<div class="placeholder"><div><h3>Cantina aguardando cadastro</h3><p>Cadastre ${escapeHtml(missing)} antes de registrar vendas.</p></div></div>`;
        }
        const walletOptions = wallets.map((wallet) => `<option value="${wallet.id}">${escapeHtml(wallet.residente_nome)} — saldo ${escapeHtml(formatReais(wallet.saldo))}</option>`).join("");
        const productOptions = products.map((product) => `<option value="${product.id}">${escapeHtml(product.nome)} — ${escapeHtml(formatReais(product.valor))}</option>`).join("");
        const productsView = `<div class="canteen-products">${products.map((product) => `<article class="canteen-product"><span>Produto</span><strong>${escapeHtml(product.nome)}</strong><b>${escapeHtml(formatReais(product.valor))}</b></article>`).join("")}</div>`;
        const form = `<form class="canteen-checkout" id="canteen-sale-form"><h3>Registrar compra</h3><div class="field"><label for="canteen-wallet">Residente</label><select id="canteen-wallet" name="carteira_id" required>${walletOptions}</select></div><div class="field"><label for="canteen-item">Produto</label><select id="canteen-item" name="item_id" required>${productOptions}</select></div><div class="field"><label for="canteen-quantity">Quantidade</label><input id="canteen-quantity" name="quantidade" type="number" min="1" step="1" value="1" required></div><p class="login-error" data-canteen-error role="alert"></p><button class="button" type="submit">Confirmar compra</button></form>`;
        const history = renderTable(dados.vendas, [["Data", "data_movimentacao", formatDate], ["Residente", "residente_nome"], ["Produto", "item_nome"], ["Quantidade", "quantidade"], ["Total", "valor_total", formatReais]]);
        return `<div class="canteen-layout"><section><h3 class="section-title">Produtos disponíveis</h3>${productsView}</section>${form}</div><h3 class="section-title">Últimas vendas</h3>${history}`;
    }

    async function renderProducts() {
        const { dados } = await api("/api/itens");
        const table = renderTable(dados, [["Produto", "nome"], ["Código de barras", "codigo_barras"], ["Categoria", "categoria"], ["Unidade", "unidade_medida"], ["Preço", "valor_atual", formatReais], ["Estoque", "estoque_atual"], ["Mínimo", "estoque_minimo"], ["Situação", "ativo", formatActive]]);
        return `<div class="toolbar"><div></div><button class="button" type="button" data-action="open-new-product">Novo produto</button></div>${table}`;
    }

    async function renderCollaborators() {
        const { dados } = await api("/api/colaboradores");
        return `<div class="toolbar"><div></div><button class="button" type="button" data-action="open-new-collaborator">Novo colaborador</button></div>${renderTable(dados, [["Nome", "nome"], ["CPF", "cpf", formatCpf], ["Status", "status"], ["Criado em", "criado_em", formatDateTime]])}`;
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
        return `<div class="toolbar report-controls"><div class="toolbar__group"><div class="field"><label for="report-type">Relatório</label><select id="report-type"><option value="financeiro">Financeiro - fluxo de caixa</option><option value="despesas_setor">Despesas por setor</option><option value="internacoes">Internações</option><option value="residentes">Residentes</option><option value="cantina">Cantina - vendas</option><option value="carteiras">Carteiras</option><option value="estoque">Estoque da Cantina</option><option value="colaboradores">Colaboradores</option></select></div><div class="field"><label for="report-start">Data inicial</label><input id="report-start" type="date" value="${start}"></div><div class="field"><label for="report-end">Data final</label><input id="report-end" type="date" value="${today}"></div></div><div class="report-actions"><button class="button" type="button" data-action="apply-report">Visualizar</button><button class="button button--secondary" type="button" data-action="print-report">Imprimir A4</button></div></div><div data-report-results>${await renderInstitutionalReport("financeiro", start, today)}</div>`;
    }

    async function refreshReport(panel) {
        const type = panel.querySelector("#report-type").value;
        const start = panel.querySelector("#report-start").value;
        const end = panel.querySelector("#report-end").value;
        const target = panel.querySelector("[data-report-results]");
        target.innerHTML = loadingState();
        try { target.innerHTML = await renderInstitutionalReport(type, start, end); }
        catch (error) { target.innerHTML = errorState(error.message); }
    }

    async function renderInstitutionalReport(type, start, end) {
        const { dados } = await api(`/api/relatorios?tipo=${encodeURIComponent(type)}&data_inicio=${encodeURIComponent(start)}&data_fim=${encodeURIComponent(end)}`);
        const summary = dados.resumo.map((item) => `<article><span>${escapeHtml(item.rotulo)}</span><strong>${escapeHtml(formatReportValue(item.valor, item.formato))}</strong></article>`).join("");
        const head = dados.colunas.map((column) => `<th>${escapeHtml(column.rotulo)}</th>`).join("");
        const body = dados.linhas.length ? dados.linhas.map((row) => `<tr>${dados.colunas.map((column) => `<td>${escapeHtml(formatReportValue(row[column.campo], column.formato))}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${dados.colunas.length}">Nenhum registro encontrado para este relatório.</td></tr>`;
        const period = dados.usa_periodo ? `<p>Período: ${formatDate(dados.data_inicio)} a ${formatDate(dados.data_fim)}</p>` : "";
        return `<article class="print-report"><header class="print-report__header"><div class="print-report__mark">CF</div><div><strong>CLÍNICA DA CRUZ DE REABILITAÇÃO</strong><span>Controle institucional</span></div></header><section class="print-report__title"><p>RELATÓRIO INSTITUCIONAL</p><h3>${escapeHtml(dados.titulo)}</h3>${period}</section><div class="print-report__summary">${summary}</div><div class="print-report__table"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div><footer class="print-report__footer"><span>Emitido em ${formatDateTime(dados.emitido_em)}</span><span>Clínica da Cruz de Reabilitação</span></footer></article>`;
    }

    function formatReportValue(value, format) {
        if (value === null || value === undefined || value === "") return "—";
        if (format === "centavos") return formatMoney(value);
        if (format === "reais") return formatReais(value);
        if (format === "data") return formatDate(value);
        if (format === "data_hora") return formatDateTime(value);
        if (format === "cpf") return formatCpf(value);
        if (format === "ativo") return formatActive(value);
        return String(value);
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
    function emptyState(title = "Nenhum registro encontrado", message = "Não há dados cadastrados para esta consulta.") { return `<div class="placeholder"><div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(message)}</p></div></div>`; }
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

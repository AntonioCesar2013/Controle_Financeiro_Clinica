import { createApi } from "./core/api.js";
import { setFormBusy } from "./components/forms.js";
import {
    emptyState,
    errorState,
    loadingState,
    metric,
    renderActionTable,
    renderTable,
} from "./components/renderers.js";
import {
    escapeHtml,
    formatActive,
    formatCpf,
    formatDate,
    formatDateTime,
    formatDocument,
    formatMoney,
    formatPhone,
    formatOptionalReais,
    formatReais,
    formatReversal,
    formatYesNo,
    valueOrDash,
    valueOrStatus,
} from "./utils/formatters.js";
import { applyInputMask, applyInputMasks } from "./utils/masks.js";


    const app = document.querySelector("#app");
    const layers = {};
    let panelSequence = 0;
    const canteenCart = new Map();
    let canteenState = { wallets: [], products: [] };
    let selectedCanteenWalletId = "";
    let selectedWalletId = "";
    let walletResidents = [];
    let monthlyState = [];
    let activePanelName = "dashboard";

    const api = createApi({
        onUnauthorized: (message) => showLogin(false, message),
    });

    const panels = {
        dashboard: ["Dashboard", "Visão gerencial", renderDashboard],
        financeiro: ["Financeiro", "Operações financeiras", renderDashboard],
        contas_receber: ["Contas a receber", "Financeiro", renderReceivables],
        mensalidades: ["Mensalidades", "Controle por residente", renderMonthlyFees],
        contas_pagar: ["Contas a pagar", "Financeiro", renderPayables],
        caixa: ["Fluxo de caixa", "Financeiro", renderCashFlow],
        despesas: ["Despesas", "Financeiro", renderExpenses],
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
        app.addEventListener("input", handleInput);
        app.addEventListener("pointerdown", (event) => {
            const panel = event.target.closest(".panel");
            if (panel) panel.style.zIndex = String(++panelSequence);
        });
        document.addEventListener("keydown", handleKeydown);
        // TESTES: reative esta linha para tornar o login obrigatório novamente.
        // checkAccess();
        openGeneralMenu();
        openMainPanel("dashboard");
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
        if (action === "open-new-convenio") openConvenioForm();
        if (action === "toggle-password") togglePassword(trigger);
        if (action === "logout") logout();
        if (action === "apply-report") refreshReport(trigger.closest(".panel"));
        if (action === "print-report") window.print();
        if (action === "open-financial-form") openFinancialForm(trigger.dataset.kind, trigger.dataset.id);
        if (action === "financial-history") openFinancialHistory(trigger.dataset.kind, trigger.dataset.id);
        if (action === "cancel-payable") runFinancialCommand("/api/contas-pagar/cancelar", { conta_id: trigger.dataset.id }, "Cancelar esta conta?", "contas_pagar");
        if (action === "delete-financial-entry") runFinancialCommand(trigger.dataset.kind === "saida" ? "/api/pagamentos-saida/excluir" : "/api/recebimentos/excluir", trigger.dataset.kind === "saida" ? { pagamento_id: trigger.dataset.id } : { recebimento_id: trigger.dataset.id }, "Estornar este lançamento?", trigger.dataset.kind === "saida" ? "contas_pagar" : "contas_receber");
        if (action === "deactivate-expense") runFinancialCommand("/api/despesas/desativar", { id: trigger.dataset.id }, "Inativar esta despesa?", "despesas");
        if (action === "open-wallet-form") openWalletForm(trigger.dataset.kind, trigger.dataset.id, trigger.dataset.value, trigger.dataset.date);
        if (action === "open-wallet-resident-search") openWalletResidentSearch();
        if (action === "select-wallet-resident") selectWalletResident(trigger.dataset.id);
        if (action === "wallet-status") runMaintenanceCommand("/api/carteiras/status", { carteira_id: trigger.dataset.id, ativo: trigger.dataset.ativo }, "Alterar a situação desta carteira?", "carteiras");
        if (action === "wallet-reversal") runMaintenanceCommand("/api/carteiras/movimentacoes/estornar", { movimentacao_id: trigger.dataset.id, motivo: "Estorno realizado pela tela" }, "Estornar esta movimentação? O saldo e o estoque serão recalculados.", "carteiras");
        if (action === "open-maintenance-form") openMaintenanceForm(trigger.dataset.kind, trigger.dataset.id);
        if (action === "product-history") openProductHistory(trigger.dataset.id);
        if (action === "canteen-cart-change") changeCanteenQuantity(trigger.dataset.id, Number(trigger.dataset.delta));
        if (action === "canteen-cart-remove") removeCanteenProduct(trigger.dataset.id);
        if (action === "canteen-cart-clear") clearCanteenCart();
        if (action === "open-canteen-resident-search") openCanteenResidentSearch();
        if (action === "select-canteen-resident") selectCanteenResident(trigger.dataset.id);
        if (action === "open-monthly-resident-search") openMonthlyResidentSearch();
        if (action === "select-monthly-resident") selectMonthlyResident(trigger.dataset.id);
        if (action === "cloud-publish") runCloudCommand("/api/sincronizacao/publicar", "Publicar a versão atual na pasta do Google Drive?");
        if (action === "cloud-update") runCloudCommand("/api/sincronizacao/atualizar", "Atualizar a cópia local com a versão mais recente?");
        if (action === "canteen-sale-reversal") runMaintenanceCommand("/api/cantina/vendas/estornar", { venda_id: trigger.dataset.id, motivo: "Venda estornada no caixa" }, "Estornar o cupom inteiro? O saldo e o estoque serão devolvidos.", "cantina");
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (event.target.matches("#login-form")) return submitLogin(event.target);
        if (event.target.matches("#setup-form")) return submitSetup(event.target);
        if (event.target.matches("#resident-form")) return submitResident(event.target);
        if (event.target.matches("#collaborator-form")) return submitCollaborator(event.target);
        if (event.target.matches("#canteen-sale-form")) return submitCanteenSale(event.target);
        if (event.target.matches("#canteen-scan-form")) return scanCanteenCode(event.target);
        if (event.target.matches("#canteen-checkout-form")) return submitCanteenCheckout(event.target);
        if (event.target.matches("#product-form")) return submitProduct(event.target);
        if (event.target.matches("#guardian-form")) return submitGuardian(event.target);
        if (event.target.matches("#internment-form")) return submitInternment(event.target);
        if (event.target.matches("#convenio-form")) return submitConvenio(event.target);
        if (event.target.matches(".financial-form")) return submitFinancialForm(event.target);
        if (event.target.matches(".maintenance-form")) return submitMaintenanceForm(event.target);
    }

    function handleChange(event) {
        if (event.target.matches("#wallet-resident")) refreshWalletDetail(event.target);
        if (event.target.matches("#canteen-wallet")) refreshCanteenCart();
        if (event.target.matches("#canteen-product-search")) addSearchedCanteenProduct(event.target);
        if (event.target.matches("#monthly-resident, #monthly-status")) refreshMonthlyFees();
        if (event.target.matches("#internment-modality")) updateInternmentMode(event.target.value);
    }

    function handleInput(event) {
        if (event.target.matches("#wallet-resident-lookup")) renderWalletResidentResults(event.target.value);
        if (event.target.matches("input[data-mask]")) applyInputMask(event.target);
        if (event.target.matches("#canteen-resident-lookup")) renderCanteenResidentResults(event.target.value);
        if (event.target.matches("#monthly-resident-lookup")) renderMonthlyResidentResults(event.target.value);
    }

    function handleKeydown(event) {
        if (event.target.matches("#canteen-product-search") && event.key === "Enter") {
            event.preventDefault();
            addSearchedCanteenProduct(event.target);
            return;
        }
        if (layers.auth.children.length || event.key !== "Escape") return;
        if (layers.modal.children.length) closeLayer("modal");
        else if (layers.auxiliary.children.length) closeLayer("auxiliary");
        else if (layers.main.children.length) closeLayer("main");
    }

    function showLogin(firstAccess = false, message = "") {
        ["main", "menu", "auxiliary", "modal"].forEach((name) => closeLayer(name, false));
        const fields = firstAccess
            ? '<div class="field"><label for="setup-name">Nome</label><input id="setup-name" name="nome" autocomplete="name" required></div><div class="field"><label for="login-user">CPF</label><input id="login-user" name="cpf" inputmode="numeric" autocomplete="username" data-mask="cpf" maxlength="14" required></div>'
            : '<div class="field"><label for="login-user">CPF</label><input id="login-user" name="cpf" inputmode="numeric" autocomplete="username" data-mask="cpf" maxlength="14" required></div>';
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
            ["mensalidades", "Mensalidades", "Pagas, vencidas e a vencer", "open-panel"],
            ["contas_pagar", "Contas a pagar", "Vencimentos e pagamentos", "open-panel"],
            ["caixa", "Fluxo de caixa", "Entradas, saídas e resultado", "open-panel"],
            ["despesas", "Despesas", "Setores e classificações", "open-panel"],
            ["", "Sair", "Encerrar esta sessão", "logout"],
        ], true);
        openMainPanel("financeiro");
    }

    function renderMenu(title, eyebrow, items, back = false) {
        const body = `<div class="menu-context">${back ? '<button class="menu-context__back" type="button" data-action="open-general-menu">← Menu geral</button>' : ""}<nav class="menu-grid" aria-label="${title}">${items.map(([id, label, description, action]) => `<button class="menu-item${id === activePanelName ? " is-active" : ""}" type="button" data-action="${action}"${id ? ` data-panel="${id}"` : ""}${id === activePanelName ? ' aria-current="page"' : ""}><strong>${label}</strong><span>${description}</span></button>`).join("")}</nav></div>`;
        layers.menu.replaceChildren(createPanel({ id: back ? "financial-menu" : "general-menu", title, eyebrow, body, size: "menu", closable: false }));
    }

    function syncMenuSelection() {
        layers.menu.querySelectorAll(".menu-item[data-panel]").forEach((item) => {
            const selected = item.dataset.panel === activePanelName;
            item.classList.toggle("is-active", selected);
            if (selected) item.setAttribute("aria-current", "page");
            else item.removeAttribute("aria-current");
        });
    }

    async function openMainPanel(name, { preserveCanteenResident = false, preserveWalletResident = false } = {}) {
        const definition = panels[name];
        if (!definition) return;
        if (name === "cantina" && !preserveCanteenResident) selectedCanteenWalletId = "";
        if (name === "carteiras" && !preserveWalletResident) selectedWalletId = "";
        activePanelName = name;
        syncMenuSelection();
        closeLayer("auxiliary", false);
        closeLayer("modal", false);
        closeLayer("main", false);
        const [title, eyebrow, renderer] = definition;
        layers.main.append(createPanel({ id: `panel-${name}`, title, eyebrow, body: loadingState() }));
        const panel = layers.main.querySelector(".panel");
        try { panel.querySelector(".panel__body").innerHTML = await renderer(); }
        catch (error) { panel.querySelector(".panel__body").innerHTML = errorState(error.message); }
        requestAnimationFrame(() => panel.focus({ preventScroll: true }));
    }

    function createPanel({ id = `panel-${++panelSequence}`, title, eyebrow, body, footer = "", size = "large", modal = false, closable = true }) {
        const wrapper = document.createElement("div");
        wrapper.innerHTML = `${modal ? '<div class="panel-backdrop panel-backdrop--modal"></div>' : ""}<section class="panel panel--${size}" id="${id}" role="${modal ? "alertdialog" : "dialog"}" aria-labelledby="${id}-title" tabindex="-1"><header class="panel__header"><div class="panel__heading">${eyebrow ? `<p class="panel__eyebrow">${eyebrow}</p>` : ""}<h2 class="panel__title" id="${id}-title">${title}</h2></div>${closable ? `<button class="panel__close" type="button" data-action="close-panel" aria-label="Fechar ${title}">&times;</button>` : ""}</header><div class="panel__body">${body}</div>${footer ? `<footer class="panel__footer">${footer}</footer>` : ""}</section>`;
        const fragment = document.createDocumentFragment();
        applyInputMasks(wrapper);
        while (wrapper.firstChild) fragment.append(wrapper.firstChild);
        return fragment;
    }

    function closePanel(panel) { if (panel) panel.parentElement.replaceChildren(); }
    function closeLayer(name) { if (layers[name]) layers[name].replaceChildren(); }

    function showAlert(title, message) {
        layers.modal.replaceChildren(createPanel({ title, body: `<div class="modal-message"><span class="modal-message__icon">i</span><p>${escapeHtml(message)}</p></div>`, footer: '<button class="button" type="button" data-action="close-panel">OK</button>', size: "small", modal: true }));
    }

    function openResidentForm() {
        const body = '<form class="login-form" id="resident-form"><div class="field"><label for="resident-name">Nome</label><input id="resident-name" name="nome" required></div><div class="field"><label for="resident-cpf">CPF</label><input id="resident-cpf" name="cpf" inputmode="numeric" data-mask="cpf" maxlength="14" placeholder="000.000.000-00" required></div><div class="field"><label for="resident-city">Cidade de origem</label><input id="resident-city" name="cidade_origem"></div><p class="login-error" id="resident-error" role="alert"></p><button class="button" type="submit">Salvar residente</button></form>';
        layers.auxiliary.replaceChildren(createPanel({ title: "Novo residente", eyebrow: "Cadastro", body, size: "medium" }));
    }

    function openCollaboratorForm() {
        const body = `
            <form class="login-form" id="collaborator-form">
                <div class="field"><label for="collaborator-name">Nome</label><input id="collaborator-name" name="nome" autocomplete="name" required></div>
                <div class="field"><label for="collaborator-cpf">CPF</label><input id="collaborator-cpf" name="cpf" inputmode="numeric" autocomplete="off" data-mask="cpf" maxlength="14" placeholder="000.000.000-00" required></div>
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
            <div class="field"><label for="product-category">Categoria</label><input id="product-category" name="categoria" list="product-categories" placeholder="Ex.: Bebidas, doces, higiene ou Serviços"><datalist id="product-categories"><option value="Bebidas"></option><option value="Doces"></option><option value="Higiene"></option><option value="Serviços"></option></datalist></div>
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
        const body = `<form class="login-form" id="guardian-form"><div class="field"><label for="guardian-name">Nome</label><input id="guardian-name" name="nome" required></div><div class="field"><label for="guardian-cpf">CPF ou CNPJ</label><input id="guardian-cpf" name="cpf" inputmode="numeric" data-mask="document" maxlength="18" placeholder="000.000.000-00" required></div><div class="field"><label for="guardian-phone">Telefone</label><input id="guardian-phone" name="telefone" type="tel" inputmode="numeric" data-mask="phone" maxlength="15" placeholder="(00) 00000-0000"></div><div class="field"><label for="guardian-email">E-mail</label><input id="guardian-email" name="email" type="email"></div><p class="login-error" data-guardian-error role="alert"></p><button class="button" type="submit">Salvar responsável</button></form>`;
        layers.auxiliary.replaceChildren(createPanel({ title: "Novo responsável", eyebrow: "Cadastro", body, size: "medium" }));
        requestAnimationFrame(() => document.getElementById("guardian-name")?.focus());
    }

    async function openInternmentForm() {
        try {
            const [residentsResponse, guardiansResponse, agreementsResponse] = await Promise.all([api("/api/residentes"), api("/api/responsaveis"), api("/api/convenios")]);
            const residents = residentsResponse.dados || [];
            const guardians = guardiansResponse.dados || [];
            if (!residents.length || !guardians.length) {
                showAlert("Cadastro necessário", "Cadastre pelo menos um residente e um responsável antes de criar a internação.");
                return;
            }
            const residentOptions = residents.map((item) => `<option value="${item.id}">${escapeHtml(item.nome)}</option>`).join("");
            const guardianOptions = guardians.map((item) => `<option value="${item.id}">${escapeHtml(item.nome)}</option>`).join("");
            const agreementOptions = (agreementsResponse.dados || []).filter((item) => Number(item.ativo) === 1).map((item) => `<option value="${item.id}">${escapeHtml(item.nome)} — ${formatMoney(item.valor_diaria)} por dia</option>`).join("");
            const today = new Date().toISOString().slice(0, 10);
            const body = `<form class="login-form" id="internment-form"><div class="field"><label for="internment-resident">Residente</label><select id="internment-resident" name="residente_id" required>${residentOptions}</select></div><div class="field"><label for="internment-guardian">Responsável</label><select id="internment-guardian" name="responsavel_id" required>${guardianOptions}</select></div><div class="field"><label for="internment-modality">Modalidade de residência</label><select id="internment-modality" name="modalidade" required><option value="PARTICULAR">Particular</option><option value="SOCIAL">Social</option><option value="CONVENIO">Convênio</option><option value="VOLUNTARIO">Voluntário</option></select></div><div class="field"><label for="internment-date">Data de acolhimento</label><input id="internment-date" name="data_acolhimento" type="date" value="${today}" required></div><div class="field" data-period-field><label for="internment-period">Período de tratamento (meses)</label><input id="internment-period" name="periodo_tratamento" type="number" min="1" step="1" required></div><div class="field" data-agreement-field hidden><label for="internment-agreement">Convênio</label><select id="internment-agreement" name="convenio_id"><option value="">Selecione</option>${agreementOptions}</select><small>O valor é calculado pela diária e pelos dias de tratamento em cada mês.</small></div><div data-particular-fields><div class="field"><label for="internment-contract">Valor do contrato</label><input id="internment-contract" name="valor_contrato" type="number" min="0" step="0.01" value="0" required></div><div class="field"><label for="internment-welcome">Valor do acolhimento</label><input id="internment-welcome" name="valor_acolhimento" type="number" min="0" step="0.01" value="0" required></div><div class="field"><label for="internment-monthly">Mensalidade</label><input id="internment-monthly" name="valor_mensalidade" type="number" min="0" step="0.01" value="0" required></div></div><div class="field" data-volunteer-field hidden><label for="internment-services">Serviços prestados à clínica</label><textarea id="internment-services" name="servicos_voluntario" rows="4" placeholder="Descreva as atividades combinadas"></textarea></div><p class="form-note" data-internment-note>O residente ficará ativo somente enquanto esta internação estiver dentro do período contratado.</p><p class="login-error" data-internment-error role="alert"></p><button class="button" type="submit">Salvar internação</button></form>`;
            layers.auxiliary.replaceChildren(createPanel({ title: "Nova internação", eyebrow: "Acolhimento e contrato", body, size: "medium" }));
        } catch (error) { showAlert("Não foi possível abrir", error.message); }
    }

    function updateInternmentMode(mode) {
        const form = document.querySelector("#internment-form");
        if (!form) return;
        const particular = mode === "PARTICULAR";
        const agreement = mode === "CONVENIO";
        const volunteer = mode === "VOLUNTARIO";
        form.querySelector("[data-particular-fields]").hidden = !particular;
        form.querySelector("[data-agreement-field]").hidden = !agreement;
        form.querySelector("[data-volunteer-field]").hidden = !volunteer;
        form.querySelector("[data-period-field]").hidden = volunteer;
        ["valor_contrato", "valor_acolhimento", "valor_mensalidade"].forEach((name) => form.elements[name].required = particular);
        form.elements.convenio_id.required = agreement;
        form.elements.servicos_voluntario.required = volunteer;
        form.elements.periodo_tratamento.required = !volunteer;
        form.querySelector("[data-internment-note]").textContent = volunteer ? "A permanência não tem prazo e continuará ativa até o encerramento manual." : mode === "SOCIAL" ? "O contrato terá período definido, sem gerar cobranças." : agreement ? "As cobranças serão separadas por mês conforme as diárias do período." : "O residente ficará ativo somente enquanto esta internação estiver dentro do período contratado.";
    }

    function openConvenioForm() {
        const body = `<form class="login-form" id="convenio-form"><div class="field"><label for="agreement-name">Nome do convênio</label><input id="agreement-name" name="nome" required></div><div class="field"><label for="agreement-rate">Valor da diária</label><input id="agreement-rate" name="valor_diaria" type="number" min="0" step="0.01" required></div><p class="login-error" data-agreement-error role="alert"></p><button class="button" type="submit">Salvar convênio</button></form>`;
        layers.auxiliary.replaceChildren(createPanel({ title: "Novo convênio", eyebrow: "Internações", body, size: "medium" }));
    }

    async function openFinancialForm(kind, id = "") {
        try {
            const today = new Date().toISOString().slice(0, 10);
            const needsRegistrations = ["despesa", "conta", "editar_setor"].includes(kind);
            const registrations = needsRegistrations ? (await api("/api/financeiro/cadastros")).dados : null;
            const definitions = {
                setor: ["Novo setor", "/api/setores", "despesas", '<div class="field"><label for="financial-name">Nome</label><input id="financial-name" name="nome" required></div>'],
                pagamento: ["Registrar pagamento", "/api/pagamentos-saida", "contas_pagar", `<input type="hidden" name="conta_pagar_id" value="${escapeHtml(id)}"><div class="field"><label for="financial-date">Data</label><input id="financial-date" name="data_pagamento" type="date" value="${today}" required></div>${moneyField("Valor pago")} ${paymentFields()}`],
                recebimento: ["Registrar recebimento", "/api/recebimentos", "contas_receber", `<input type="hidden" name="cobranca_id" value="${escapeHtml(id)}"><div class="field"><label for="financial-date">Data</label><input id="financial-date" name="data_pagamento" type="date" value="${today}" required></div>${moneyField("Valor recebido")} ${paymentFields()}`],
                recebimento_mensalidade: ["Receber mensalidade", "/api/recebimentos", "mensalidades", `<input type="hidden" name="cobranca_id" value="${escapeHtml(id)}"><div class="field"><label for="financial-date">Data</label><input id="financial-date" name="data_pagamento" type="date" value="${today}" required></div>${moneyField("Valor recebido")} ${paymentFields()}`],
                desconto: ["Aplicar desconto", "/api/cobrancas/desconto", "contas_receber", `<input type="hidden" name="cobranca_id" value="${escapeHtml(id)}">${moneyField("Valor do desconto")}`],
            };

            if (kind === "despesa") {
                const sectors = registrations.setores.filter((item) => Number(item.ativo) === 1);
                if (!sectors.length) {
                    showAlert("Cadastro necessário", "Cadastre ao menos um setor ativo.");
                    return;
                }
                definitions.despesa = ["Nova despesa", "/api/despesas", "despesas", `<div class="field"><label for="expense-sector">Setor</label><select id="expense-sector" name="setor_id" required>${selectOptions(sectors)}</select></div><div class="field"><label for="expense-description">Descrição</label><input id="expense-description" name="descricao" required></div><div class="field"><label for="expense-nature">Natureza</label><select id="expense-nature" name="natureza"><option value="FIXA">Fixa</option><option value="VARIAVEL">Variável</option><option value="EXTRAORDINARIA">Extraordinária</option></select></div><label class="form-note"><input name="recorrente" type="checkbox" value="1"> Despesa recorrente</label>`];
            }
            if (kind === "conta") {
                const activeExpenses = registrations.despesas.filter((item) => Number(item.ativo) === 1);
                if (!activeExpenses.length) {
                    showAlert("Cadastro necessário", "Cadastre uma despesa ativa antes de lançar uma conta.");
                    return;
                }
                definitions.conta = ["Nova conta a pagar", "/api/contas-pagar", "contas_pagar", `<div class="field"><label for="payable-expense">Despesa</label><select id="payable-expense" name="despesa_id" required>${activeExpenses.map((item) => `<option value="${item.id}">${escapeHtml(item.descricao)} — ${escapeHtml(item.setor_nome)}</option>`).join("")}</select></div><div class="field"><label for="financial-due-date">Vencimento</label><input id="financial-due-date" name="data_vencimento" type="date" value="${today}" required></div>${moneyField("Valor da conta")}`];
            }
            if (kind === "editar_setor") {
                const collection = registrations.setores;
                const item = collection.find((entry) => String(entry.id) === String(id));
                if (!item) throw new Error("Cadastro não encontrado.");
                definitions[kind] = ["Editar setor", "/api/setores/editar", "despesas", `<input type="hidden" name="id" value="${item.id}"><div class="field"><label for="financial-name">Nome</label><input id="financial-name" name="nome" value="${escapeHtml(item.nome)}" required></div><div class="field"><label for="financial-active">Situação</label><select id="financial-active" name="ativo"><option value="1"${Number(item.ativo) === 1 ? " selected" : ""}>Ativo</option><option value="0"${Number(item.ativo) === 0 ? " selected" : ""}>Inativo</option></select></div>`];
            }

            const definition = definitions[kind];
            if (!definition) return;
            const [title, endpoint, refresh, fields] = definition;
            const body = `<form class="login-form financial-form" data-endpoint="${endpoint}" data-refresh="${refresh}" data-kind="${kind}">${fields}<p class="login-error" data-financial-error role="alert"></p><button class="button" type="submit">Salvar</button></form>`;
            layers.auxiliary.replaceChildren(createPanel({ title, eyebrow: "Financeiro", body, size: "medium" }));
            requestAnimationFrame(() => layers.auxiliary.querySelector("input:not([type=hidden]), select")?.focus());
        } catch (error) { showAlert("Não foi possível abrir", error.message); }
    }

    function moneyField(label) {
        return `<div class="field"><label for="financial-value">${label}</label><input id="financial-value" name="valor" type="number" min="0.01" step="0.01" required></div>`;
    }

    function paymentFields() {
        return '<div class="field"><label for="financial-method">Forma</label><select id="financial-method" name="forma_pagamento"><option value="PIX">PIX</option><option value="DINHEIRO">Dinheiro</option><option value="CARTAO">Cartão</option><option value="TRANSFERENCIA">Transferência</option><option value="BOLETO">Boleto</option></select></div><div class="field"><label for="financial-note">Observação</label><textarea id="financial-note" name="observacao" rows="3"></textarea></div>';
    }

    function selectOptions(items) {
        return items.map((item) => `<option value="${item.id}">${escapeHtml(item.nome)}</option>`).join("");
    }

    async function submitFinancialForm(form) {
        const data = Object.fromEntries(new FormData(form));
        if (form.dataset.kind === "despesa" && !data.recorrente) data.recorrente = "0";
        const errorElement = form.querySelector("[data-financial-error]");
        setFormBusy(form, true);
        try {
            await api(form.dataset.endpoint, { method: "POST", body: data });
            const refresh = form.dataset.refresh;
            closeLayer("auxiliary");
            await openMainPanel(refresh, { preserveWalletResident: refresh === "carteiras" });
            showAlert("Operação concluída", "O registro financeiro foi salvo com sucesso.");
        } catch (error) { errorElement.textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function runFinancialCommand(endpoint, body, confirmation, refreshPanel) {
        if (confirmation && !window.confirm(confirmation)) return;
        try {
            await api(endpoint, { method: "POST", body });
            closeLayer("auxiliary");
            await openMainPanel(refreshPanel, { preserveWalletResident: refreshPanel === "carteiras" });
            showAlert("Operação concluída", "O lançamento foi atualizado com sucesso.");
        } catch (error) { showAlert("Não foi possível concluir", error.message); }
    }

    async function openFinancialHistory(kind, id) {
        try {
            const isOutgoing = kind === "saida";
            const endpoint = isOutgoing ? `/api/contas-pagar/pagamentos?id=${encodeURIComponent(id)}` : `/api/contas-receber/recebimentos?id=${encodeURIComponent(id)}`;
            const { dados } = await api(endpoint);
            const columns = isOutgoing
                ? [["Data", "data_pagamento", formatDate], ["Valor", "valor", formatMoney], ["Forma", "forma_pagamento"], ["Observação", "observacao"]]
                : [["Data", "data_recebimento", formatDate], ["Valor", "valor", formatMoney], ["Forma", "forma_recebimento"], ["Observação", "observacao"]];
            const body = renderActionTable(dados, columns, (row) => `<button class="button button--danger" type="button" data-action="delete-financial-entry" data-kind="${isOutgoing ? "saida" : "entrada"}" data-id="${row.id}">Estornar</button>`);
            layers.auxiliary.replaceChildren(createPanel({ title: isOutgoing ? "Pagamentos da conta" : "Recebimentos da cobrança", eyebrow: "Histórico individual", body, size: "large" }));
        } catch (error) { showAlert("Não foi possível consultar", error.message); }
    }

    async function openWalletForm(kind, id = "", value = "", movementDate = "") {
        try {
            const today = new Date().toISOString().slice(0, 10);
            let title;
            let endpoint;
            let fields;
            if (kind === "create") {
                const [{ dados: residents }, { dados: wallets }] = await Promise.all([api("/api/residentes"), api("/api/carteiras")]);
                const walletResidents = new Set(wallets.map((wallet) => String(wallet.residente_id)));
                const eligible = residents.filter((resident) => Number(resident.ativo) === 1 && !walletResidents.has(String(resident.id)));
                if (!eligible.length) {
                    showAlert("Nenhum residente disponível", "Todos os residentes ativos já possuem carteira ou ainda não há internação vigente.");
                    return;
                }
                title = "Criar carteira"; endpoint = "/api/carteiras";
                fields = `<div class="field"><label for="wallet-resident-new">Residente</label><select id="wallet-resident-new" name="residente_id">${selectOptions(eligible)}</select></div>${moneyField("Saldo inicial")}`;
                fields = fields.replace('name="valor"', 'name="saldo_inicial"').replace('min="0.01"', 'min="0"').replace(" required></div>", ' value="0" required></div>');
            } else if (kind === "credit") {
                title = "Adicionar crédito"; endpoint = "/api/carteiras/credito";
                fields = `<input type="hidden" name="carteira_id" value="${escapeHtml(id)}">${moneyField("Valor do crédito")}<div class="field"><label for="wallet-date">Data</label><input id="wallet-date" name="data_movimentacao" type="date" value="${today}" required></div>`;
            } else {
                title = "Corrigir crédito"; endpoint = "/api/carteiras/movimentacoes/corrigir";
                fields = `<input type="hidden" name="movimentacao_id" value="${escapeHtml(id)}">${moneyField("Valor corrigido")}<div class="field"><label for="wallet-date">Data</label><input id="wallet-date" name="data_movimentacao" type="date" value="${escapeHtml(movementDate || today)}" required></div><div class="field"><label for="wallet-reason">Motivo</label><input id="wallet-reason" name="motivo" value="Correção de crédito" required></div>`;
                fields = fields.replace('name="valor"', `name="valor" value="${escapeHtml(value)}"`);
            }
            const body = `<form class="login-form maintenance-form" data-endpoint="${endpoint}" data-refresh="carteiras">${fields}<p class="login-error" data-maintenance-error role="alert"></p><button class="button" type="submit">Salvar</button></form>`;
            layers.auxiliary.replaceChildren(createPanel({ title, eyebrow: "Carteiras", body, size: "medium" }));
        } catch (error) { showAlert("Não foi possível abrir", error.message); }
    }

    async function openMaintenanceForm(kind, id) {
        try {
            const today = new Date().toISOString().slice(0, 10);
            let title;
            let endpoint;
            let refresh;
            let fields;
            if (kind === "resident") {
                const item = (await api("/api/residentes")).dados.find((row) => String(row.id) === String(id));
                title = "Editar residente"; endpoint = "/api/residentes/editar"; refresh = "residentes";
                fields = `<input type="hidden" name="id" value="${item.id}"><div class="field"><label>Nome</label><input name="nome" value="${escapeHtml(item.nome)}" required></div><div class="field"><label>CPF</label><input name="cpf" value="${escapeHtml(item.cpf)}" inputmode="numeric" data-mask="cpf" maxlength="14" required></div><div class="field"><label>Cidade de origem</label><input name="cidade_origem" value="${escapeHtml(item.cidade_origem || "")}"></div><p class="form-note">A situação é calculada automaticamente pela internação.</p>`;
            } else if (kind === "guardian") {
                const item = (await api("/api/responsaveis")).dados.find((row) => String(row.id) === String(id));
                title = "Editar responsável"; endpoint = "/api/responsaveis/editar"; refresh = "responsaveis";
                fields = `<input type="hidden" name="id" value="${item.id}"><div class="field"><label>Nome</label><input name="nome" value="${escapeHtml(item.nome)}" required></div><div class="field"><label>CPF ou CNPJ</label><input name="cpf" value="${escapeHtml(item.cpf)}" inputmode="numeric" data-mask="document" maxlength="18" required></div><div class="field"><label>Telefone</label><input name="telefone" type="tel" inputmode="numeric" data-mask="phone" maxlength="15" value="${escapeHtml(item.telefone || "")}"></div><div class="field"><label>E-mail</label><input name="email" type="email" value="${escapeHtml(item.email || "")}"></div>${activeSelect(item.ativo)}`;
            } else if (kind === "internment-end") {
                title = "Encerrar internação"; endpoint = "/api/internacoes/encerrar"; refresh = "internacoes";
                fields = `<input type="hidden" name="id" value="${escapeHtml(id)}"><div class="field"><label>Data de encerramento</label><input name="data_encerramento" type="date" value="${today}" required></div><div class="field"><label>Motivo</label><textarea name="motivo" rows="3" required></textarea></div>`;
            } else if (kind === "internment-guardian") {
                const guardians = (await api("/api/responsaveis")).dados.filter((row) => Number(row.ativo) === 1);
                title = "Alterar responsável principal"; endpoint = "/api/internacoes/responsavel"; refresh = "internacoes";
                fields = `<input type="hidden" name="id" value="${escapeHtml(id)}"><div class="field"><label>Responsável</label><select name="responsavel_id">${selectOptions(guardians)}</select></div>`;
            } else if (kind === "product") {
                const item = (await api("/api/itens")).dados.find((row) => String(row.id) === String(id));
                title = "Editar produto"; endpoint = "/api/itens/editar"; refresh = "itens";
                fields = `<input type="hidden" name="id" value="${item.id}"><div class="field"><label>Nome</label><input name="nome" value="${escapeHtml(item.nome)}" required></div><div class="field"><label>Código de barras</label><input name="codigo_barras" value="${escapeHtml(item.codigo_barras || "")}"></div><div class="field"><label>Categoria</label><input name="categoria" value="${escapeHtml(item.categoria || "")}"></div><div class="field"><label>Descrição</label><textarea name="descricao" rows="3">${escapeHtml(item.descricao || "")}</textarea></div><div class="field"><label>Unidade</label><input name="unidade_medida" value="${escapeHtml(item.unidade_medida)}" required></div><div class="field"><label>Estoque mínimo</label><input name="estoque_minimo" type="number" min="0" value="${item.estoque_minimo}" required></div>${activeSelect(item.ativo)}`;
            } else if (kind === "product-stock") {
                title = "Movimentar estoque"; endpoint = "/api/itens/estoque"; refresh = "itens";
                fields = `<input type="hidden" name="item_id" value="${escapeHtml(id)}"><div class="field"><label>Operação</label><select name="tipo" required><option value="ENTRADA">Entrada — acrescentar</option><option value="SAIDA">Saída — retirar</option></select></div><div class="field"><label>Quantidade</label><input name="quantidade" type="number" min="1" step="1" required></div><div class="field"><label>Data da movimentação</label><input name="data_movimentacao" type="date" value="${today}" required></div><div class="field"><label>Motivo</label><input name="motivo" placeholder="Ex.: compra, perda, consumo interno" required></div><div class="field"><label>Custo unitário (opcional)</label><input name="custo_unitario" type="number" min="0" step="0.01"></div><div class="field"><label>Fornecedor (opcional)</label><input name="fornecedor"></div><div class="field"><label>Nota ou documento (opcional)</label><input name="documento"></div><div class="field"><label>Lote (opcional)</label><input name="lote"></div><div class="field"><label>Validade (opcional)</label><input name="data_validade" type="date"></div>`;
            } else if (kind === "product-price") {
                title = "Novo preço"; endpoint = "/api/itens/precos"; refresh = "itens";
                fields = `<input type="hidden" name="item_id" value="${escapeHtml(id)}">${moneyField("Novo preço")}<div class="field"><label>Válido desde</label><input name="data_inicio_valor" type="date" value="${today}" required></div>`;
            } else if (kind === "collaborator") {
                const item = (await api("/api/colaboradores")).dados.find((row) => String(row.id) === String(id));
                title = "Editar colaborador"; endpoint = "/api/colaboradores/editar"; refresh = "colaboradores";
                fields = `<input type="hidden" name="id" value="${item.id}"><div class="field"><label>Nome</label><input name="nome" value="${escapeHtml(item.nome)}" required></div><div class="field"><label>CPF</label><input name="cpf" value="${escapeHtml(item.cpf)}" inputmode="numeric" data-mask="cpf" maxlength="14" required></div><div class="field"><label>Status</label><select name="status"><option value="ATIVO"${item.status === "ATIVO" ? " selected" : ""}>Ativo</option><option value="INATIVO"${item.status === "INATIVO" ? " selected" : ""}>Inativo</option></select></div>`;
            } else if (kind === "collaborator-password") {
                title = "Redefinir senha"; endpoint = "/api/colaboradores/senha"; refresh = "colaboradores";
                fields = `<input type="hidden" name="id" value="${escapeHtml(id)}"><div class="field"><label>Nova senha</label><input name="senha" type="password" minlength="8" required></div><div class="field"><label>Confirmar senha</label><input name="confirmacao_senha" type="password" minlength="8" required></div>`;
            }
            if (!fields) throw new Error("Operação não encontrada.");
            const body = `<form class="login-form maintenance-form" data-endpoint="${endpoint}" data-refresh="${refresh}" data-kind="${kind}">${fields}<p class="login-error" data-maintenance-error role="alert"></p><button class="button" type="submit">Salvar</button></form>`;
            layers.auxiliary.replaceChildren(createPanel({ title, eyebrow: "Manutenção de cadastro", body, size: "medium" }));
        } catch (error) { showAlert("Não foi possível abrir", error.message); }
    }

    function activeSelect(active) {
        return `<div class="field"><label>Situação</label><select name="ativo"><option value="1"${Number(active) === 1 ? " selected" : ""}>Ativo</option><option value="0"${Number(active) === 0 ? " selected" : ""}>Inativo</option></select></div>`;
    }

    async function submitMaintenanceForm(form) {
        const data = Object.fromEntries(new FormData(form));
        const errorElement = form.querySelector("[data-maintenance-error]");
        if (form.dataset.kind === "collaborator-password") {
            if (data.senha !== data.confirmacao_senha) {
                errorElement.textContent = "A confirmação da senha não confere.";
                return;
            }
            delete data.confirmacao_senha;
        }
        setFormBusy(form, true);
        try {
            await api(form.dataset.endpoint, { method: "POST", body: data });
            const refresh = form.dataset.refresh;
            closeLayer("auxiliary");
            await openMainPanel(refresh, { preserveWalletResident: refresh === "carteiras" });
            showAlert("Cadastro atualizado", "A alteração foi salva com sucesso.");
        } catch (error) { errorElement.textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function runMaintenanceCommand(endpoint, body, confirmation, refreshPanel) {
        if (confirmation && !window.confirm(confirmation)) return;
        try {
            await api(endpoint, { method: "POST", body });
            closeLayer("auxiliary");
            await openMainPanel(refreshPanel, { preserveWalletResident: refreshPanel === "carteiras" });
            showAlert("Operação concluída", "O registro foi atualizado com sucesso.");
        } catch (error) { showAlert("Não foi possível concluir", error.message); }
    }

    async function openProductHistory(id) {
        try {
            const { dados } = await api(`/api/itens/historico?id=${encodeURIComponent(id)}`);
            const prices = renderTable(dados.precos, [["Válido desde", "data_inicio_valor", formatDate], ["Preço", "valor", formatReais], ["Situação", "ativo", formatActive]]);
            const stock = renderTable(dados.estoque, [["Data", "data_movimentacao", formatDate], ["Tipo", "tipo"], ["Cupom", "venda_id"], ["Anterior", "quantidade_anterior"], ["Movimento", "quantidade_movimentada"], ["Atual", "quantidade_atual"], ["Custo unitário", "custo_unitario", formatOptionalReais], ["Fornecedor", "fornecedor"], ["Documento", "documento"], ["Lote", "lote"], ["Validade", "data_validade", formatDate], ["Motivo", "motivo"]]);
            layers.auxiliary.replaceChildren(createPanel({ title: "Histórico do produto", eyebrow: "Preços e estoque", body: `<h3 class="section-title">Preços</h3>${prices}<h3 class="section-title">Ajustes de estoque</h3>${stock}`, size: "large" }));
        } catch (error) { showAlert("Não foi possível consultar", error.message); }
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
            await openMainPanel("cantina", { preserveCanteenResident: true });
            showAlert("Compra concluída", `${resultado.residente} comprou ${resultado.quantidade}x ${resultado.item}. Saldo atual: ${formatReais(resultado.saldo)}.`);
        } catch (error) { errorElement.textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function scanCanteenCode(form) {
        const input = form.elements.codigo_barras;
        const errorElement = form.querySelector("[data-canteen-scan-error]");
        const code = input.value.trim();
        if (!code) return;
        setFormBusy(form, true);
        try {
            const saleDate = document.querySelector("#canteen-sale-date")?.value || new Date().toISOString().slice(0, 10);
            const { dados: product } = await api(`/api/cantina/produto?codigo=${encodeURIComponent(code)}&data=${encodeURIComponent(saleDate)}`);
            if (!product?.sucesso) throw new Error(product?.erro || "Produto não encontrado.");
            addProductToCanteen(product);
            input.value = "";
            errorElement.textContent = "";
        } catch (error) { errorElement.textContent = error.message; }
        finally {
            setFormBusy(form, false);
            requestAnimationFrame(() => input.focus());
        }
    }

    function addSearchedCanteenProduct(input) {
        const search = input.value.trim().toLocaleLowerCase("pt-BR");
        if (!search) return;
        const product = canteenState.products.find((item) => {
            const name = String(item.nome || "").toLocaleLowerCase("pt-BR");
            const barcode = String(item.codigo_barras || "").toLocaleLowerCase("pt-BR");
            return search === name || search === barcode || search === `${name} — ${barcode || "sem código"}`;
        });
        if (!product) return;
        addProductToCanteen(product);
        input.value = "";
        input.focus();
    }

    function isCanteenService(product) {
        return ["SERVICO", "SERVICOS"].includes(String(product?.categoria || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toUpperCase());
    }

    function openCanteenResidentSearch() {
        const body = `<div class="field"><label for="canteen-resident-lookup">Pesquisar residente</label><input id="canteen-resident-lookup" type="search" autocomplete="off" placeholder="Digite o nome do residente" autofocus></div><div class="resident-search-results" data-canteen-resident-results></div>`;
        layers.auxiliary.replaceChildren(createPanel({ id: "canteen-resident-search", title: "Pesquisar residente", eyebrow: "Cantina", body, size: "medium" }));
        renderCanteenResidentResults("");
        setTimeout(() => document.querySelector("#canteen-resident-lookup")?.focus(), 0);
    }

    function renderCanteenResidentResults(value) {
        const target = document.querySelector("[data-canteen-resident-results]");
        if (!target) return;
        const search = String(value || "").trim().toLocaleLowerCase("pt-BR");
        const wallets = canteenState.wallets.filter((wallet) => String(wallet.residente_nome || "").toLocaleLowerCase("pt-BR").includes(search));
        target.innerHTML = wallets.length
            ? wallets.map((wallet) => `<button class="resident-search-result" type="button" data-action="select-canteen-resident" data-id="${wallet.id}"><strong>${escapeHtml(wallet.residente_nome)}</strong><span>Saldo ${escapeHtml(formatReais(wallet.saldo))}</span></button>`).join("")
            : emptyState("Residente não encontrado", "Revise o nome informado.");
    }

    function selectCanteenResident(walletId) {
        const select = document.querySelector("#canteen-wallet");
        if (!select) return;
        select.value = String(walletId);
        closeLayer("auxiliary");
        refreshCanteenCart();
    }

    function addProductToCanteen(product) {
        const key = String(product.id);
        const current = canteenCart.get(key);
        const quantity = (current?.quantity || 0) + 1;
        if (!isCanteenService(product) && quantity > Number(product.estoque_atual)) {
            showAlert("Estoque insuficiente", `Há somente ${product.estoque_atual} unidade(s) de ${product.nome}.`);
            return;
        }
        canteenCart.set(key, { ...product, quantity });
        refreshCanteenCart();
    }

    function changeCanteenQuantity(id, delta) {
        const item = canteenCart.get(String(id));
        if (!item) return;
        const quantity = item.quantity + delta;
        if (quantity <= 0) canteenCart.delete(String(id));
        else if (isCanteenService(item) || quantity <= Number(item.estoque_atual)) canteenCart.set(String(id), { ...item, quantity });
        else showAlert("Estoque insuficiente", `Há somente ${item.estoque_atual} unidade(s) disponíveis.`);
        refreshCanteenCart();
    }

    function removeCanteenProduct(id) {
        canteenCart.delete(String(id));
        refreshCanteenCart();
    }

    function clearCanteenCart() {
        if (canteenCart.size && !window.confirm("Limpar todos os produtos do carrinho?")) return;
        canteenCart.clear();
        refreshCanteenCart();
    }

    function refreshCanteenCart() {
        const target = document.querySelector("[data-canteen-cart]");
        if (!target) return;
        const items = [...canteenCart.values()];
        const total = items.reduce((sum, item) => sum + Number(item.valor) * item.quantity, 0);
        const walletId = document.querySelector("#canteen-wallet")?.value;
        const wallet = canteenState.wallets.find((item) => String(item.id) === String(walletId));
        selectedCanteenWalletId = wallet ? String(wallet.id) : "";
        const balance = Number(wallet?.saldo || 0);
        const remaining = balance - total;
        const rows = items.map((item) => `<tr><td>${escapeHtml(item.nome)}</td><td>${escapeHtml(formatReais(item.valor))}</td><td><div class="canteen-quantity"><button type="button" data-action="canteen-cart-change" data-id="${item.id}" data-delta="-1">−</button><strong>${item.quantity}</strong><button type="button" data-action="canteen-cart-change" data-id="${item.id}" data-delta="1">+</button></div></td><td>${escapeHtml(formatReais(Number(item.valor) * item.quantity))}</td><td><button class="button button--danger" type="button" data-action="canteen-cart-remove" data-id="${item.id}">Remover</button></td></tr>`).join("");
        target.innerHTML = items.length ? `<div class="table-wrap"><table class="canteen-cart-table"><thead><tr><th>Produto</th><th>Unitário</th><th>Qtd.</th><th>Subtotal</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : emptyState("Carrinho vazio", "Leia um código de barras ou escolha um produto.");
        const totalElement = document.querySelector("[data-canteen-total]");
        const balanceElement = document.querySelector("[data-canteen-balance]");
        const remainingElement = document.querySelector("[data-canteen-remaining]");
        if (totalElement) totalElement.textContent = formatReais(total);
        if (balanceElement) {
            balanceElement.textContent = wallet ? formatReais(balance) : "—";
            balanceElement.classList.toggle("amount--positive", Boolean(wallet) && balance > 0);
            balanceElement.classList.toggle("amount--negative", Boolean(wallet) && balance <= 0);
        }
        if (remainingElement) {
            remainingElement.textContent = wallet ? formatReais(remaining) : "—";
            remainingElement.classList.toggle("amount--negative", Boolean(wallet) && remaining < 0);
        }
        const button = document.querySelector("#canteen-checkout-button");
        if (button) button.disabled = !items.length || !walletId;
    }

    async function submitCanteenCheckout(form) {
        const errorElement = form.querySelector("[data-canteen-error]");
        const walletId = form.elements.carteira_id.value;
        if (!walletId) {
            errorElement.textContent = "Selecione um residente antes de finalizar a compra.";
            return;
        }
        const products = [...canteenCart.values()].map((item) => ({ item_id: item.id, quantidade: item.quantity }));
        if (!products.length) {
            errorElement.textContent = "Adicione produtos ao carrinho.";
            return;
        }
        setFormBusy(form, true);
        try {
            const result = await api("/api/cantina/checkout", {
                method: "POST",
                body: { carteira_id: walletId, data_movimentacao: form.elements.data_movimentacao.value, produtos: products },
            });
            selectedCanteenWalletId = String(walletId);
            canteenCart.clear();
            await openMainPanel("cantina", { preserveCanteenResident: true });
            showAlert("Compra finalizada", `Cupom nº ${result.id}: ${result.quantidade_itens} item(ns), total ${formatReais(result.valor_total)}. Saldo atual: ${formatReais(result.saldo)}.`);
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

    async function submitConvenio(form) {
        const data = Object.fromEntries(new FormData(form));
        setFormBusy(form, true);
        try {
            await api("/api/convenios", { method: "POST", body: data });
            closeLayer("auxiliary");
            await openMainPanel("internacoes");
            showAlert("Convênio salvo", "O convênio e o valor da diária foram cadastrados.");
        } catch (error) { form.querySelector("[data-agreement-error]").textContent = error.message; }
        finally { setFormBusy(form, false); }
    }

    async function renderDashboard() {
        const { dados } = await api("/api/dashboard");
        return `<div class="metrics">${metric("Entradas do mês", dados.total_entradas, "success")}${metric("Saídas do mês", dados.total_saidas, "danger")}${metric("Resultado", dados.resultado, "primary")}${metric("A receber", dados.total_receber, "warning")}${metric("A pagar", dados.total_pagar, "warning")}</div><h3 class="section-title">Movimentações recentes</h3>${renderTable(dados.movimentacoes_recentes, [["Data", "data", formatDate], ["Descrição", "descricao"], ["Tipo", "tipo"], ["Forma", "forma_pagamento"], ["Valor", "valor", formatMoney]])}`;
    }

    async function renderResidents() {
        const { dados } = await api("/api/residentes");
        return `<div class="toolbar"><div></div><button class="button" type="button" data-action="open-new-resident">Novo residente</button></div>${renderActionTable(dados, [["Nome", "nome"], ["CPF", "cpf", formatCpf], ["Cidade de origem", "cidade_origem"], ["Situação", "ativo", formatActive]], (row) => `<button class="button button--secondary" type="button" data-action="open-maintenance-form" data-kind="resident" data-id="${row.id}">Editar</button>`)}`;
    }

    async function renderGuardians() {
        const { dados } = await api("/api/responsaveis");
        return `<div class="toolbar"><div></div><button class="button" type="button" data-action="open-new-guardian">Novo responsável</button></div>${renderActionTable(dados, [["Nome", "nome"], ["CPF/CNPJ", "cpf", formatDocument], ["Telefone", "telefone", formatPhone], ["E-mail", "email"], ["Situação", "ativo", formatActive]], (row) => `<button class="button button--secondary" type="button" data-action="open-maintenance-form" data-kind="guardian" data-id="${row.id}">Editar</button>`)}`;
    }

    async function renderInternments() {
        const { dados } = await api("/api/internacoes");
        return `<div class="toolbar"><div></div><div class="report-actions"><button class="button button--secondary" type="button" data-action="open-new-convenio">Novo convênio</button><button class="button" type="button" data-action="open-new-internment">Nova internação</button></div></div>${renderActionTable(dados, [["Residente", "residente_nome"], ["Modalidade", "modalidade"], ["Convênio", "convenio_nome"], ["Responsável", "responsavel_nome"], ["Acolhimento", "data_acolhimento", formatDate], ["Período", "periodo_tratamento", (value, row) => row.modalidade === "VOLUNTARIO" ? "Sem prazo" : `${value} meses`], ["Contrato", "valor_contrato", formatMoney], ["Diária", "valor_diaria", (value, row) => row.modalidade === "CONVENIO" ? formatMoney(value) : "—"], ["Status", "status"], ["Encerrada em", "encerrada_em", formatDate]], (row) => `<button class="button button--secondary" type="button" data-action="open-maintenance-form" data-kind="internment-guardian" data-id="${row.id}">Responsável</button>${row.status === "ATIVA" && !row.encerrada_em ? `<button class="button button--danger" type="button" data-action="open-maintenance-form" data-kind="internment-end" data-id="${row.id}">Encerrar</button>` : ""}`)}`;
    }

    async function renderWallets() {
        const { dados } = await api("/api/carteiras");
        walletResidents = dados || [];
        const toolbar = '<div class="toolbar"><div></div><button class="button" type="button" data-action="open-wallet-form" data-kind="create">Nova carteira</button></div>';
        if (!dados?.length) return `${toolbar}${emptyState("Nenhuma carteira cadastrada", "Crie uma carteira para o residente antes de consultar saldo e compras.")}`;
        const selected = dados.find((wallet) => String(wallet.id) === selectedWalletId);
        selectedWalletId = selected ? String(selected.id) : "";
        const options = `<option value=""${selected ? "" : " selected"}>Selecione um residente</option>` + dados.map((wallet) => `<option value="${wallet.id}"${String(wallet.id) === selectedWalletId ? " selected" : ""}>${escapeHtml(wallet.residente_nome)}</option>`).join("");
        const detail = selected ? await renderWalletDetail(selected.id) : walletSelectionPlaceholder();
        return `${toolbar}<div class="wallet-selector"><div class="field"><label for="wallet-resident">Residente</label><select id="wallet-resident">${options}</select></div><button class="canteen-resident-search-button" type="button" data-action="open-wallet-resident-search" aria-label="Pesquisar residente" title="Pesquisar residente">🔍</button></div><div data-wallet-detail>${detail}</div>`;
    }

    function walletSelectionPlaceholder() {
        return emptyState("Selecione um residente", "Escolha no seletor ou use a lupa para consultar o saldo e o histórico da carteira.");
    }

    function openWalletResidentSearch() {
        const body = '<div class="field"><label for="wallet-resident-lookup">Pesquisar residente</label><input id="wallet-resident-lookup" type="search" autocomplete="off" placeholder="Digite o nome do residente"></div><div class="resident-search-results" data-wallet-resident-results></div>';
        layers.auxiliary.replaceChildren(createPanel({ title: "Pesquisar residente", eyebrow: "Carteiras", body, size: "medium" }));
        renderWalletResidentResults("");
        requestAnimationFrame(() => document.querySelector("#wallet-resident-lookup")?.focus());
    }

    function renderWalletResidentResults(value) {
        const target = document.querySelector("[data-wallet-resident-results]");
        if (!target) return;
        const search = String(value || "").trim().toLocaleLowerCase("pt-BR");
        const matches = walletResidents.filter((wallet) => String(wallet.residente_nome || "").toLocaleLowerCase("pt-BR").includes(search));
        target.innerHTML = matches.length ? matches.map((wallet) => `<button class="resident-search-result" type="button" data-action="select-wallet-resident" data-id="${wallet.id}"><strong>${escapeHtml(wallet.residente_nome)}</strong><span class="${Number(wallet.saldo) > 0 ? "amount--positive" : "amount--negative"}">Saldo ${escapeHtml(formatReais(wallet.saldo))}</span></button>`).join("") : emptyState("Residente não encontrado", "Revise o nome informado.");
    }

    function selectWalletResident(walletId) {
        const select = document.querySelector("#wallet-resident");
        if (!select) return;
        select.value = String(walletId);
        closeLayer("auxiliary");
        refreshWalletDetail(select);
    }

    async function refreshWalletDetail(select) {
        const target = select.closest(".panel__body").querySelector("[data-wallet-detail]");
        const walletId = select.value;
        selectedWalletId = walletId;
        if (!walletId) {
            target.innerHTML = walletSelectionPlaceholder();
            return;
        }
        target.innerHTML = loadingState();
        try {
            const detail = await renderWalletDetail(walletId);
            if (select.value === walletId) target.innerHTML = detail;
        }
        catch (error) { if (select.value === walletId) target.innerHTML = errorState(error.message); }
    }

    async function renderWalletDetail(walletId) {
        const resultado = await api(`/api/carteiras/detalhe?id=${encodeURIComponent(walletId)}`);
        const dados = resultado.dados;
        if (!dados?.sucesso) throw new Error(dados?.erro || "Carteira não encontrada.");
        const wallet = dados.carteira;
        const credits = renderActionTable(dados.creditos, [["Data", "data_movimentacao", formatDate], ["Valor", "valor_total", formatReais], ["Situação", "estornada", formatReversal], ["Motivo do estorno", "motivo_estorno"]], (row) => Number(row.estornada) === 0 ? `<button class="button button--secondary" type="button" data-action="open-wallet-form" data-kind="correct" data-id="${row.id}" data-value="${row.valor_total}" data-date="${row.data_movimentacao}">Corrigir</button><button class="button button--danger" type="button" data-action="wallet-reversal" data-id="${row.id}">Estornar</button>` : "");
        const purchases = renderActionTable(dados.compras, [["Cupom", "venda_id"], ["Data", "data_movimentacao", formatDate], ["Produto", "item_nome"], ["Quantidade", "quantidade"], ["Valor unitário", "valor_unitario", formatReais], ["Total descontado", "valor_total", formatReais], ["Situação", "estornada", formatReversal]], (row) => Number(row.estornada) === 0 && !row.venda_id ? `<button class="button button--danger" type="button" data-action="wallet-reversal" data-id="${row.id}">Estornar compra</button>` : "");
        const walletActions = Number(wallet.ativo) === 1 ? `<button class="button" type="button" data-action="open-wallet-form" data-kind="credit" data-id="${wallet.id}">Adicionar crédito</button><button class="button button--danger" type="button" data-action="wallet-status" data-id="${wallet.id}" data-ativo="0">Inativar carteira</button>` : `<button class="button" type="button" data-action="wallet-status" data-id="${wallet.id}" data-ativo="1">Reativar carteira</button>`;
        return `<div class="toolbar"><div></div><div class="report-actions">${walletActions}</div></div><div class="wallet-summary"><article><span>Residente</span><strong>${escapeHtml(wallet.residente_nome)}</strong></article><article><span>Saldo disponível</span><strong class="${Number(wallet.saldo) > 0 ? "amount--positive" : "amount--negative"}">${escapeHtml(formatReais(wallet.saldo))}</strong></article><article><span>Situação</span><strong>${escapeHtml(formatActive(wallet.ativo))}</strong></article></div><h3 class="section-title">Créditos</h3>${credits}<h3 class="section-title">Compras na Cantina</h3>${purchases}`;
    }

    async function renderCantina() {
        const { dados } = await api("/api/cantina");
        const wallets = dados.carteiras || [];
        const products = dados.itens || [];
        canteenState = { wallets, products };
        canteenCart.clear();
        if (!wallets.length || !products.length) {
            const missing = [!wallets.length ? "uma carteira ativa para o residente" : "", !products.length ? "itens ativos com preço vigente" : ""].filter(Boolean).join(" e ");
            return `<div class="placeholder"><div><h3>Cantina aguardando cadastro</h3><p>Cadastre ${escapeHtml(missing)} antes de registrar vendas.</p></div></div>`;
        }
        const selectedWallet = wallets.find((wallet) => String(wallet.id) === selectedCanteenWalletId);
        selectedCanteenWalletId = selectedWallet ? String(selectedWallet.id) : "";
        const selectedBalance = selectedWallet ? formatReais(selectedWallet.saldo) : "—";
        const balanceClass = selectedWallet ? (Number(selectedWallet.saldo) > 0 ? "amount--positive" : "amount--negative") : "";
        const walletOptions = `<option value=""${selectedWallet ? "" : " selected"}>Selecione um residente</option>` + wallets.map((wallet) => `<option value="${wallet.id}"${String(wallet.id) === selectedCanteenWalletId ? " selected" : ""}>${escapeHtml(wallet.residente_nome)}</option>`).join("");
        const productSearchOptions = products.map((product) => `<option value="${escapeHtml(product.nome)} — ${escapeHtml(product.codigo_barras || "sem código")}">${escapeHtml(formatReais(product.valor))} — ${isCanteenService(product) ? "serviço sem estoque" : `estoque ${product.estoque_atual}`}</option>`).join("");
        const customer = `<section class="canteen-customer"><div class="field"><label for="canteen-wallet">Residente</label><select id="canteen-wallet" name="carteira_id" form="canteen-checkout-form" required>${walletOptions}</select></div><button class="canteen-resident-search-button" type="button" data-action="open-canteen-resident-search" aria-label="Pesquisar residente" title="Pesquisar residente">🔍</button><div class="canteen-balance"><span>Saldo da carteira</span><strong data-canteen-balance class="${balanceClass}">${selectedBalance}</strong></div></section>`;
        const scanner = `<section class="canteen-scanner"><h3>Leitor de código de barras</h3><form id="canteen-scan-form"><div class="field"><label for="canteen-barcode">Código</label><input id="canteen-barcode" name="codigo_barras" autocomplete="off" inputmode="numeric" placeholder="Leia o código e pressione Enter" autofocus required></div><p class="login-error" data-canteen-scan-error role="alert"></p><button class="button" type="submit">Adicionar código</button></form></section>`;
        const productSearch = `<section class="canteen-product-search"><h3>Pesquisa manual do produto</h3><div class="field"><label for="canteen-product-search">Produto</label><input id="canteen-product-search" type="search" list="canteen-product-options" autocomplete="off" placeholder="Nome ou código de barras"><datalist id="canteen-product-options">${productSearchOptions}</datalist></div><small>Selecione uma sugestão ou pressione Enter para adicionar ao cupom.</small></section>`;
        const checkout = `<form class="canteen-checkout" id="canteen-checkout-form"><div class="canteen-checkout__details"><h3>Carrinho de compras</h3><div class="field"><label for="canteen-sale-date">Data</label><input id="canteen-sale-date" name="data_movimentacao" type="date" value="${new Date().toISOString().slice(0, 10)}" required></div></div><div data-canteen-cart>${emptyState("Carrinho vazio", "Leia um código de barras ou pesquise um produto.")}</div><div class="canteen-totals"><article><span>Total</span><strong data-canteen-total>${formatReais(0)}</strong></article><article><span>Saldo após compra</span><strong data-canteen-remaining>${selectedBalance}</strong></article></div><p class="login-error" data-canteen-error role="alert"></p><div class="report-actions"><button class="button button--secondary" type="button" data-action="canteen-cart-clear">Limpar</button><button class="button" id="canteen-checkout-button" type="submit" disabled>Finalizar compra</button></div></form>`;
        setTimeout(() => { refreshCanteenCart(); document.querySelector("#canteen-barcode")?.focus(); }, 0);
        return `${customer}<div class="canteen-entry">${scanner}${productSearch}</div>${checkout}`;
    }

    async function renderProducts() {
        const { dados } = await api("/api/itens");
        const active = dados.filter((row) => Number(row.ativo) === 1).length;
        const low = dados.filter((row) => Number(row.ativo) === 1 && !isCanteenService(row) && ["REPOR", "SEM ESTOQUE"].includes(row.situacao_estoque)).length;
        const units = dados.reduce((total, row) => total + Number(row.estoque_atual || 0), 0);
        const summary = `<div class="inventory-summary"><article><span>Produtos cadastrados</span><strong>${dados.length}</strong></article><article><span>Produtos ativos</span><strong>${active}</strong></article><article><span>Precisam de reposição</span><strong class="${low ? "amount--negative" : "amount--positive"}">${low}</strong></article><article><span>Unidades em estoque</span><strong>${units}</strong></article></div>`;
        const table = renderActionTable(dados, [["Produto", "nome"], ["Código de barras", "codigo_barras"], ["Categoria", "categoria"], ["Unidade", "unidade_medida"], ["Preço", "valor_atual", formatReais], ["Estoque", "estoque_atual", (value, row) => isCanteenService(row) ? "Não se aplica" : value], ["Mínimo", "estoque_minimo", (value, row) => isCanteenService(row) ? "Não se aplica" : value], ["Reposição", "situacao_estoque", (value, row) => isCanteenService(row) ? "Não se aplica" : value], ["Cadastro", "ativo", formatActive]], (row) => `<button class="button button--secondary" type="button" data-action="open-maintenance-form" data-kind="product" data-id="${row.id}">Editar</button><button class="button button--secondary" type="button" data-action="open-maintenance-form" data-kind="product-price" data-id="${row.id}">Preço</button>${isCanteenService(row) ? "" : `<button class="button" type="button" data-action="open-maintenance-form" data-kind="product-stock" data-id="${row.id}">Movimentar</button>`}<button class="button button--secondary" type="button" data-action="product-history" data-id="${row.id}">Histórico</button>`);
        return `<div class="toolbar"><div></div><button class="button" type="button" data-action="open-new-product">Novo produto</button></div>${summary}<div class="products-report">${table}</div>`;
    }

    async function renderCollaborators() {
        const { dados } = await api("/api/colaboradores");
        return `<div class="toolbar"><div></div><button class="button" type="button" data-action="open-new-collaborator">Novo colaborador</button></div>${renderActionTable(dados, [["Nome", "nome"], ["CPF", "cpf", formatCpf], ["Status", "status"], ["Criado em", "criado_em", formatDateTime]], (row) => `<button class="button button--secondary" type="button" data-action="open-maintenance-form" data-kind="collaborator" data-id="${row.id}">Editar</button><button class="button button--secondary" type="button" data-action="open-maintenance-form" data-kind="collaborator-password" data-id="${row.id}">Redefinir senha</button>`)}`;
    }

    async function renderReceivables() {
        const { dados } = await api("/api/contas-receber");
        return renderActionTable(dados, [["Internação", "internacao_id"], ["Parcela", "numero_parcela"], ["Tipo", "tipo"], ["Vencimento", "data_vencimento", formatDate], ["Valor devido", "valor_devido", formatMoney], ["Recebido", "total_recebido", formatMoney], ["Saldo", "saldo_restante", formatMoney], ["Situação", "situacao_temporal", valueOrStatus]], (row) => {
            const open = Number(row.saldo_restante) > 0 && !["PAGA", "DESCONTADA"].includes(row.status);
            return `${open ? `<button class="button" type="button" data-action="open-financial-form" data-kind="recebimento" data-id="${row.id}">Receber</button><button class="button button--secondary" type="button" data-action="open-financial-form" data-kind="desconto" data-id="${row.id}">Desconto</button>` : ""}<button class="button button--secondary" type="button" data-action="financial-history" data-kind="entrada" data-id="${row.id}">Histórico</button>`;
        });
    }

    function monthlyStatus(row) {
        if (row.status === "PARCIAL" || row.status === "DESCONTADA") return row.status;
        if (Number(row.saldo_restante) <= 0 || row.status === "PAGA") return "PAGA";
        return String(row.data_vencimento) < new Date().toISOString().slice(0, 10) ? "VENCIDA" : "A VENCER";
    }

    function monthlyFeesContent(residentId = "", status = "") {
        const residentRows = residentId ? monthlyState.filter((row) => String(row.residente_id) === String(residentId)) : monthlyState;
        const paid = residentRows.filter((row) => monthlyStatus(row) === "PAGA");
        const overdue = residentRows.filter((row) => monthlyStatus(row) === "VENCIDA");
        const upcoming = residentRows.filter((row) => monthlyStatus(row) === "A VENCER");
        const partial = residentRows.filter((row) => monthlyStatus(row) === "PARCIAL");
        const discounted = residentRows.filter((row) => monthlyStatus(row) === "DESCONTADA");
        const rows = status ? residentRows.filter((row) => monthlyStatus(row) === status) : residentRows;
        const totals = `<div class="metrics">${metric(`Pagas (${paid.length})`, paid.reduce((sum, row) => sum + Number(row.total_recebido || 0), 0), "success")}${metric(`A vencer (${upcoming.length})`, upcoming.reduce((sum, row) => sum + Number(row.saldo_restante || 0), 0), "primary")}${metric(`Vencidas (${overdue.length})`, overdue.reduce((sum, row) => sum + Number(row.saldo_restante || 0), 0), "danger")}${metric(`Parciais (${partial.length})`, partial.reduce((sum, row) => sum + Number(row.saldo_restante || 0), 0), "warning")}${metric(`Descontadas (${discounted.length})`, discounted.reduce((sum, row) => sum + Number(row.desconto || 0), 0), "primary")}</div>`;
        const table = renderActionTable(rows, [["Residente", "residente_nome"], ["Modalidade", "modalidade"], ["Convênio", "convenio_nome"], ["Parcela", "numero_parcela"], ["Vencimento", "data_vencimento", formatDate], ["Valor", "valor_devido", formatMoney], ["Recebido", "total_recebido", formatMoney], ["Saldo", "saldo_restante", formatMoney], ["Situação", "status", (_, row) => monthlyStatus(row)]], (row) => `${monthlyStatus(row) !== "PAGA" ? `<button class="button" type="button" data-action="open-financial-form" data-kind="recebimento_mensalidade" data-id="${row.id}">Receber</button>` : ""}<button class="button button--secondary" type="button" data-action="financial-history" data-kind="entrada" data-id="${row.id}">Histórico</button>`);
        return `${totals}<div class="monthly-report">${table}</div>`;
    }

    function refreshMonthlyFees() {
        const target = document.querySelector("[data-monthly-results]");
        const residentId = document.querySelector("#monthly-resident")?.value || "";
        const status = document.querySelector("#monthly-status")?.value || "";
        if (target) target.innerHTML = monthlyFeesContent(residentId, status);
    }

    function openMonthlyResidentSearch() {
        const body = `<div class="field"><label for="monthly-resident-lookup">Pesquisar residente</label><input id="monthly-resident-lookup" type="search" autocomplete="off" placeholder="Digite o nome do residente" autofocus></div><div class="resident-search-results" data-monthly-resident-results></div>`;
        layers.auxiliary.replaceChildren(createPanel({ id: "monthly-resident-search", title: "Pesquisar residente", eyebrow: "Mensalidades", body, size: "medium" }));
        renderMonthlyResidentResults("");
        setTimeout(() => document.querySelector("#monthly-resident-lookup")?.focus(), 0);
    }

    function renderMonthlyResidentResults(value) {
        const target = document.querySelector("[data-monthly-resident-results]");
        if (!target) return;
        const search = String(value || "").trim().toLocaleLowerCase("pt-BR");
        const residents = [...new Map(monthlyState.map((row) => [String(row.residente_id), row.residente_nome])).entries()]
            .filter(([, name]) => String(name || "").toLocaleLowerCase("pt-BR").includes(search))
            .sort((a, b) => a[1].localeCompare(b[1], "pt-BR"));
        target.innerHTML = residents.length
            ? residents.map(([id, name]) => `<button class="resident-search-result" type="button" data-action="select-monthly-resident" data-id="${escapeHtml(id)}"><strong>${escapeHtml(name)}</strong><span>Selecionar</span></button>`).join("")
            : emptyState("Residente não encontrado", "Revise o nome informado.");
    }

    function selectMonthlyResident(residentId) {
        const select = document.querySelector("#monthly-resident");
        if (!select) return;
        select.value = String(residentId);
        closeLayer("auxiliary");
        refreshMonthlyFees();
    }

    async function renderMonthlyFees() {
        const { dados } = await api("/api/mensalidades");
        monthlyState = dados || [];
        const residents = [...new Map(monthlyState.map((row) => [String(row.residente_id), row.residente_nome])).entries()]
            .sort((a, b) => a[1].localeCompare(b[1], "pt-BR"));
        const options = residents.map(([id, name]) => `<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`).join("");
        return `<div class="monthly-controls"><div class="field"><label for="monthly-resident">Residente</label><select id="monthly-resident"><option value="">Todos os residentes</option>${options}</select></div><button class="monthly-search-button" type="button" data-action="open-monthly-resident-search" aria-label="Pesquisar residente" title="Pesquisar residente">🔍</button><div class="field"><label for="monthly-status">Situação</label><select id="monthly-status"><option value="">Todas as mensalidades</option><option value="A VENCER">A pagar</option><option value="PAGA">Pagas</option><option value="VENCIDA">Vencidas</option><option value="DESCONTADA">Descontadas</option><option value="PARCIAL">Parcialmente pagas</option></select></div></div><div data-monthly-results>${monthlyFeesContent()}</div>`;
    }

    async function renderPayables() {
        const { dados } = await api("/api/contas-pagar");
        const table = renderActionTable(dados, [["Descrição", "despesa_descricao"], ["Setor", "setor_nome"], ["Natureza", "natureza"], ["Vencimento", "data_vencimento", formatDate], ["Valor", "valor", formatMoney], ["Pago", "total_pago", formatMoney], ["Restante", "restante", formatMoney], ["Status", "status"]], (row) => {
            const open = Number(row.restante) > 0 && !["PAGA", "CANCELADA"].includes(row.status);
            return `${open ? `<button class="button" type="button" data-action="open-financial-form" data-kind="pagamento" data-id="${row.id}">Pagar</button><button class="button button--danger" type="button" data-action="cancel-payable" data-id="${row.id}">Cancelar</button>` : ""}<button class="button button--secondary" type="button" data-action="financial-history" data-kind="saida" data-id="${row.id}">Histórico</button>`;
        });
        return `<div class="toolbar"><div></div><button class="button" type="button" data-action="open-financial-form" data-kind="conta">Nova conta</button></div>${table}`;
    }

    async function renderExpenses() {
        const { dados } = await api("/api/financeiro/cadastros");
        const sectors = renderActionTable(dados.setores, [["Setor", "nome"], ["Situação", "ativo", formatActive]], (row) => `<button class="button button--secondary" type="button" data-action="open-financial-form" data-kind="editar_setor" data-id="${row.id}">Editar</button>`);
        const expenses = renderActionTable(dados.despesas, [["Descrição", "descricao"], ["Setor", "setor_nome"], ["Natureza", "natureza"], ["Recorrente", "recorrente", formatYesNo], ["Situação", "ativo", formatActive]], (row) => Number(row.ativo) === 1 ? `<button class="button button--danger" type="button" data-action="deactivate-expense" data-id="${row.id}">Inativar</button>` : "");
        return `<div class="toolbar"><div></div><div class="report-actions"><button class="button button--secondary" type="button" data-action="open-financial-form" data-kind="setor">Novo setor</button><button class="button" type="button" data-action="open-financial-form" data-kind="despesa">Nova despesa</button></div></div><h3 class="section-title">Setores</h3>${sectors}<h3 class="section-title">Despesas cadastradas</h3>${expenses}`;
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
        const [financeResponse, cloudResponse] = await Promise.all([api("/api/configuracoes"), api("/api/sincronizacao/status")]);
        const dados = financeResponse.dados;
        const cloud = cloudResponse.dados;
        const financial = dados ? renderTable([dados], [["Aplicar juros", "aplicar_juros", formatYesNo], ["Tipo de juros", "tipo_juros"], ["Valor dos juros", "valor_juros"], ["Aplicar multa", "aplicar_multa", formatYesNo], ["Tipo da multa", "tipo_multa"], ["Valor da multa", "valor_multa"]]) : emptyState();
        const actions = cloud.ativa ? `<div class="report-actions">${cloud.modo === "ESCRITA" ? '<button class="button" type="button" data-action="cloud-publish">Publicar versão</button>' : '<button class="button" type="button" data-action="cloud-update">Buscar versão mais recente</button>'}</div>` : "";
        const cloudTable = renderTable([cloud], [["Situação", "ativa", (value) => value ? "Ativa" : "Desativada"], ["Modo preparado", "modo"], ["Pasta Google Drive", "pasta_google_drive", valueOrDash], ["Última versão", "ultima_versao", valueOrDash], ["Versões disponíveis", "quantidade_versoes"]]);
        return `<h3 class="section-title">Parâmetros financeiros</h3>${financial}<h3 class="section-title">Sincronização futura com Google Drive</h3><p class="form-note">${escapeHtml(cloud.mensagem)}</p>${actions}${cloudTable}`;
    }

    async function runCloudCommand(endpoint, message) {
        if (!window.confirm(message)) return;
        try {
            const result = await api(endpoint, { method: "POST", body: {} });
            await openMainPanel("configuracoes");
            showAlert("Sincronização concluída", result.arquivo ? `Versão: ${result.arquivo}` : "Operação concluída.");
        } catch (error) { showAlert("Não foi possível sincronizar", error.message); }
    }

    async function renderResource(url, columns) {
        const { dados } = await api(url);
        return renderTable(dados, columns);
    }


initialize();

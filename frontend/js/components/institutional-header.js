const logoUrl = new URL("../../assets/logo-clinica.svg", import.meta.url).href;

export function renderInstitutionalHeader() {
    return `<header class="institutional-header"><img class="institutional-header__logo" src="${logoUrl}" width="110" height="110" alt="Logo da Clínica da Cruz de Reabilitação"><div class="institutional-header__details"><span class="institutional-header__name">CLÍNICA DA CRUZ DA REABILITAÇÃO</span><strong>Rua Padre Donizette, 180, Centro, Jesuítas - PR</strong><span>CNPJ:45.923.316/0001-93 - Fone:(45)99949-9220</span></div></header>`;
}

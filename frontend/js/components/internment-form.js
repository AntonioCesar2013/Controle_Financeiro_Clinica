import { escapeHtml, formatMoney } from '../utils/formatters.js';
import { normalizeSearch } from './filters.js';
import { currencyValue } from '../utils/masks.js';

export function groupInternmentPeople(people, internments, key, search = '') {
    const active = new Set(internments.filter(i => i.status === 'ATIVA').map(i => String(i[key])));
    const tokens = normalizeSearch(search).split(/\s+/).filter(Boolean);
    const visible = people.filter(p => tokens.every(t => normalizeSearch(`${p.nome} ${p.cpf || ''}`).includes(t)
        || String(p.cpf || '').replace(/\D/g, '').includes(t)))
        .slice().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
    return [visible.filter(p => !active.has(String(p.id))), visible.filter(p => active.has(String(p.id)))];
}

export function internmentPeopleOptions(groups, selected = '') {
    const option = p => `<option value="${escapeHtml(p.id)}"${String(p.id) === String(selected) ? ' selected' : ''}>${escapeHtml(p.nome)}${Number(p.ativo) === 0 ? ' (inativo)' : ''}</option>`;
    return '<option value="">Selecione</option>' + groups[0].map(option).join('')
        + (groups[1].length ? '<option disabled>──────── Com internação ativa ────────</option>' + groups[1].map(option).join('') : '');
}

export function internmentSearchField(kind, label, name, options) {
    return `<div class="field internment-person"><label for="internment-${kind}">${label}</label>
        <div class="internment-person__select"><select id="internment-${kind}" name="${name}" required>${options}</select>
        <button type="button" class="button button--secondary" data-internment-search="${kind}" aria-expanded="false" aria-controls="internment-search-${kind}">Pesquisar</button></div>
        <div id="internment-search-${kind}" class="internment-person__search" hidden>
        <label for="internment-query-${kind}">Pesquisar ${label.toLowerCase()} por nome ou CPF/CNPJ</label>
        <input type="search" id="internment-query-${kind}" autocomplete="off">
        <div class="internment-person__results" aria-live="polite"></div></div></div>`;
}

export function bindInternmentSearch(form, residents, guardians, internments) {
    for (const [kind, people, key] of [['resident', residents, 'residente_id'], ['guardian', guardians, 'responsavel_id']]) {
        const button = form.querySelector(`[data-internment-search="${kind}"]`);
        const box = form.querySelector(`#internment-search-${kind}`);
        const input = box.querySelector('input');
        const results = box.querySelector('.internment-person__results');
        const select = form.querySelector(`#internment-${kind}`);
        const render = () => {
            const groups = groupInternmentPeople(people, internments, key, input.value);
            const rows = group => group.map(p => `<button type="button" class="internment-person__result" data-person-id="${escapeHtml(p.id)}">${escapeHtml(p.nome)}${p.cpf ? ` · ${escapeHtml(p.cpf)}` : ''}</button>`).join('');
            results.innerHTML = groups.flat().length
                ? `${groups[0].length ? '<p>Sem internação ativa</p>' + rows(groups[0]) : ''}${groups[1].length ? '<hr><p>Com internação ativa</p>' + rows(groups[1]) : ''}`
                : '<p>Nenhum cadastro encontrado.</p>';
        };
        button.addEventListener('click', () => {
            box.hidden = !box.hidden;
            button.setAttribute('aria-expanded', String(!box.hidden));
            if (!box.hidden) { render(); input.focus(); }
        });
        input.addEventListener('input', render);
        input.addEventListener('keydown', event => { if (event.key === 'Enter') event.preventDefault(); });
        results.addEventListener('click', event => {
            const result = event.target.closest('[data-person-id]');
            if (!result) return;
            select.value = result.dataset.personId;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            box.hidden = true;
            button.setAttribute('aria-expanded', 'false');
            select.focus();
        });
    }
}

export function internmentContractTotal(welcome, monthly, months) {
    const cents = value => Math.round(currencyValue(value) * 100);
    return formatMoney(cents(welcome) + cents(monthly) * Number(months || 0));
}

export function internmentMoneyPayload(data) {
    const result = { ...data };
    for (const name of ['valor_contrato', 'valor_acolhimento', 'valor_mensalidade']) {
        if (name in result) result[name] = currencyValue(result[name]).toFixed(2);
    }
    return result;
}

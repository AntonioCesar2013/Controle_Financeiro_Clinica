import { escapeHtml, formatMoney, formatDate, localDate } from '../utils/formatters.js';
import { renderTable } from './renderers.js';
import { setFormBusy } from './forms.js';

function formatDateTime(value) {
    if (!value) return '—';
    return new Date(String(value).replace(' ', 'T') + 'Z').toLocaleString('pt-BR');
}

const labels = { RECEBER: 'Contas a receber', PAGAR: 'Contas a pagar', CARTEIRA: 'Carteiras', ESTOQUE: 'Estoque físico' };
const destination = { PENDENTE: 'Pendente', RECEBIMENTO: 'Recebimentos da clínica', CARTEIRA: 'Carteiras — separado', OUTRA_RECEITA: 'Outra receita da clínica' };
const error = '<p class="login-error" data-conference-error role="alert"></p>';
const identification = '<div class="field"><label>Conferido por<input name="responsavel" maxlength="2000" required></label></div><div class="field"><label>Documentos usados e observações<textarea name="observacao" maxlength="2000" required></textarea></label></div>';
const reason = '<div class="field"><label>Motivo / documento de referência<textarea name="motivo" maxlength="2000" required></textarea></label></div>';

export function balanceFields(items) {
    return Object.entries(labels).map(([type, title]) => `<section><h3>${title}</h3>${items.filter(r => r.tipo === type).map(r => `
        <div class="field"><label>${escapeHtml(r.nome)} <small>(${escapeHtml(r.chave)}) — sistema: ${type === 'ESTOQUE' ? `${r.valor} ${escapeHtml(r.unidade)}` : formatMoney(r.valor)}</small>
        <input type="number" step="${type === 'ESTOQUE' ? '1' : '0.01'}" ${type === 'CARTEIRA' ? '' : 'min="0"'} data-conference-value="${escapeHtml(r.chave)}" placeholder="Valor conferido no controle externo" required></label></div>`).join('') || '<p>Nenhum item a conferir.</p>'}</section>`).join('');
}

function historyBalances(rows) {
    return rows.map(r => `<details><summary>#${r.id} — ${escapeHtml(r.status)} — ${formatDateTime(r.criada_em)} — ${escapeHtml(r.responsavel)}</summary>
        <p>${escapeHtml(r.observacao)}</p>${renderTable(r.dados.itens, [['Item','nome'],['Grupo','tipo'],['Sistema','valor',(v,row)=>row.tipo==='ESTOQUE'?v:formatMoney(v)],['Conferido','conferido',(v,row)=>row.tipo==='ESTOQUE'?v:formatMoney(v)],['Diferença','diferenca',(v,row)=>row.tipo==='ESTOQUE'?v:formatMoney(v)]])}</details>`).join('') || '<p>Nenhuma conferência registrada.</p>';
}

function totals(dados) {
    return `<p><strong>Clínica:</strong> entradas ${formatMoney(dados.clinica.entradas)} · saídas ${formatMoney(dados.clinica.saidas)} · resultado ${formatMoney(dados.clinica.entradas-dados.clinica.saidas)}</p>
        <p><strong>Carteiras, separadas:</strong> saldo de abertura ${formatMoney(dados.carteiras.saldo_abertura)} · créditos ${formatMoney(dados.carteiras.creditos)} · compras ${formatMoney(dados.carteiras.compras)} · saldo final ${formatMoney(dados.carteiras.saldo_fechamento)}</p>`;
}

export function createConference({ api, refresh, showPanel, showAlert }) {
    let view = 'banco';
    let competence = localDate().slice(0,7);
    let data;
    let selectedEntry;

    async function render() {
        const urls = { banco: '/api/conciliacao', saldos: '/api/conferencia/saldos', mensal: `/api/conferencia/mensal?competencia=${encodeURIComponent(competence)}` };
        const { dados } = await api(urls[view]);
        data = dados;
        const navigation = `<div class="toolbar"><div class="toolbar__group">${[['banco','1. Conciliação bancária'],['saldos','2. Conferência de saldos'],['mensal','3. Fechamento mensal']].map(([v,t])=>`<button class="button ${view===v?'':'button--secondary'}" data-action="conference-view" data-view="${v}">${t}</button>`).join('')}</div></div>`;
        return `${navigation}<p class="form-note">As carteiras são controladas separadamente das receitas da clínica. Conferências registram evidências e não alteram os saldos.</p>${view==='banco'?bank():view==='saldos'?balances():monthly()}`;
    }

    function bank() {
        const pending = data.entradas.filter(r=>r.destino==='PENDENTE');
        return `<p><strong>${pending.length} entradas pendentes — ${formatMoney(pending.reduce((s,r)=>s+r.valor,0))}.</strong> Identifique cada entrada pelos documentos. O vínculo usa lançamentos já cadastrados; se faltar um recebimento ou crédito, registre-o na tela correspondente e volte aqui.</p>
            <p>Ao vincular recebimentos, o caixa passa a contar uma única entrada na data bancária. Créditos vinculados ficam fora do caixa da clínica. Uma entrada pode corresponder a vários lançamentos do mesmo destino, com soma exata.</p>
            <div class="table-wrap"><table><thead><tr><th>Data</th><th>Descrição / documento</th><th>Valor</th><th>Situação</th><th>Ação</th></tr></thead><tbody>${data.entradas.map(r=>`<tr><td>${formatDate(r.data_entrada)}</td><td>${escapeHtml(r.descricao)}<br><small>${escapeHtml(r.origem_documento)}</small></td><td>${formatMoney(r.valor)}</td><td>${escapeHtml(destination[r.destino])}</td><td><button class="button button--secondary" data-action="conference-entry" data-id="${r.id}">${r.conciliacao_id?'Ver / desfazer':'Conciliar'}</button></td></tr>`).join('')}</tbody></table></div>
            <details><summary>Histórico das conciliações</summary>${renderTable(data.historico,[['ID','id'],['Entrada','entrada_id'],['Destino','destino'],['Motivo','motivo'],['Registrada em','criada_em',formatDateTime],['Desfeita em','desfeita_em',v=>v?formatDateTime(v):'—'],['Motivo da correção','motivo_desfazer']])}</details>`;
    }

    function balances() {
        return `<p>Posição atual em ${formatDate(data.data)}. Compare cada conta, carteira e produto com contratos, controles externos e contagem física. Inclui contas futuras e carteiras inativas. Preencha todos os campos, inclusive os zeros.</p>
            <p>A receber: <strong>${formatMoney(data.totais.RECEBER)}</strong> · A pagar: <strong>${formatMoney(data.totais.PAGAR)}</strong> · Carteiras: <strong>${formatMoney(data.totais.CARTEIRA)}</strong></p>
            <form class="login-form conference-form" data-operation="saldos" data-hash="${data.assinatura}">${balanceFields(data.itens)}${identification}${error}<button class="button" type="submit">Registrar comparação dos saldos</button></form>
            <h3>Conferências anteriores</h3><p>Uma conferência é uma fotografia do momento registrado. Movimentações posteriores exigem uma nova conferência quando necessário.</p>${historyBalances(data.historico)}`;
    }

    function monthly() {
        const active = data.historico.find(r=>!r.reaberto_em);
        const fields = [['entradas','Entradas da clínica'],['saidas','Saídas da clínica'],['creditos','Créditos das carteiras'],['compras','Compras nas carteiras'],['saldo_carteiras','Saldo final das carteiras']];
        return `<form class="conference-form toolbar" data-operation="periodo"><div class="field"><label>Mês<input type="month" name="competencia" value="${competence}" required></label></div><button class="button" type="submit">Consultar mês</button></form>
            <p><strong>Situação: ${active?escapeHtml(active.status):'ABERTO'}</strong> · ${data.pendentes} entradas bancárias pendentes.</p>${totals(data)}
            <p>O fechamento registra os movimentos efetivos do mês e o saldo das carteiras. Contas a receber, a pagar e estoque são conferidos na aba de saldos atuais. Ajustes retroativos são permitidos e fazem o fechamento aparecer como REVISAR; reabra com justificativa e registre uma nova revisão.</p>
            ${active ? `<form class="login-form conference-form" data-operation="reabrir" data-id="${active.id}">${active.status==='REVISAR'?'<p role="alert">Os dados atuais diferem do fechamento guardado. Confira os ajustes antes de fechar novamente.</p>':''}${reason}${error}<button class="button button--secondary" type="submit">Reabrir mês com justificativa</button></form>` : `<form class="login-form conference-form" data-operation="fechar" data-hash="${data.assinatura}">${fields.map(([key,label])=>`<div class="field"><label>${label} — valor conferido nos documentos<input type="number" step="0.01" ${key==='saldo_carteiras'?'':'min="0"'} data-conference-value="${key}" required></label></div>`).join('')}${identification}${error}<button class="button" type="submit" ${data.pendentes || data.fim>=localDate()?'disabled':''}>Registrar fechamento do mês</button>${data.fim>=localDate()?'<p>O fechamento fica disponível após o último dia do mês.</p>':''}</form>`}
            <details><summary>Movimentos atuais da clínica</summary>${renderTable(data.clinica.movimentos,[['Data','data',formatDate],['Descrição','descricao'],['Tipo','tipo'],['Valor','valor',formatMoney]])}</details>
            <details><summary>Movimentos atuais das carteiras (inclui estornados, sem efeito nos totais)</summary>${renderTable(data.carteiras.movimentos,[['Data','data_movimentacao',formatDate],['Carteira','carteira_id'],['Tipo','tipo'],['Estornado','estornada',v=>v?'Sim':'Não'],['Valor','valor_total',formatMoney]])}</details>
            <h3>Revisões preservadas</h3>${data.historico.map(r=>`<details><summary>Revisão ${r.revisao} — ${escapeHtml(r.status)} — ${formatDateTime(r.fechado_em)}</summary><p>Conferido por ${escapeHtml(r.responsavel)}. ${escapeHtml(r.observacao)}</p>${r.reaberto_em?`<p>Reaberto em ${formatDateTime(r.reaberto_em)}: ${escapeHtml(r.motivo_reabertura)}</p>`:''}${totals(r.dados)}${renderTable(r.dados.clinica.movimentos,[['Data','data',formatDate],['Descrição','descricao'],['Tipo','tipo'],['Valor original','valor',formatMoney]])}</details>`).join('') || '<p>Nenhum fechamento registrado.</p>'}`;
    }

    function entry(id) {
        selectedEntry = data.entradas.find(r=>r.id===Number(id));
        const r = selectedEntry;
        if (!r) return;
        const title = `${formatDate(r.data_entrada)} — ${formatMoney(r.valor)}`;
        if (r.conciliacao_id) {
            const original = JSON.parse(r.vinculos_originais || '[]');
            showPanel('Conciliação registrada', `<p>${escapeHtml(r.descricao)} — ${title}</p><p>${escapeHtml(destination[r.destino])}: ${escapeHtml(r.motivo)}</p>${renderTable(original,[['Lançamento','id'],['Valor','valor_conciliado',formatMoney]])}<form class="login-form conference-form" data-operation="desfazer" data-id="${r.conciliacao_id}"><p>Desfazer torna a entrada pendente e devolve os recebimentos ao cálculo separado do caixa, até a nova conciliação.</p>${reason}${error}<button class="button" type="submit">Desfazer conciliação</button></form>`);
        } else {
            showPanel('Conciliar entrada bancária', `<p>${escapeHtml(r.descricao)} — ${title}</p><form class="login-form conference-form" data-operation="vincular" data-id="${r.id}"><div class="field"><label>Destino<select name="destino" data-conference-destination><option value="RECEBIMENTO">Recebimentos da clínica</option><option value="CARTEIRA">Créditos das carteiras (separado)</option><option value="OUTRA_RECEITA">Outra receita da clínica, sem cobrança</option></select></label></div><div data-conference-targets>${targets('RECEBIMENTO')}</div>${reason}${error}<button class="button" type="submit">Confirmar conciliação</button></form>`);
        }
    }

    function targets(type) {
        if (type==='OUTRA_RECEITA') return '<p>Use somente para receita da clínica que não corresponde a uma cobrança ou carteira. Identifique sua origem no motivo.</p>';
        const rows = type==='RECEBIMENTO'?data.recebimentos:data.creditos;
        return `<p>Marque os lançamentos correspondentes. A soma deve ser ${formatMoney(selectedEntry.valor)}. As datas podem diferir: confirme pelos documentos.</p>${rows.map(r=>`<label class="form-note"><input type="checkbox" name="vinculo" value="${r.id}"> #${r.id} — ${escapeHtml(r.nome)} — ${formatDate(r.data)} — ${formatMoney(r.valor)}</label>`).join('') || '<p>Nenhum lançamento disponível. Cadastre o recebimento/crédito e atualize esta tela.</p>'}`;
    }

    async function click(trigger) {
        if (trigger.dataset.action==='conference-view') { view=trigger.dataset.view; await refresh(); }
        if (trigger.dataset.action==='conference-entry') entry(trigger.dataset.id);
    }

    function change(target) {
        if (target.matches('[data-conference-destination]')) target.form.querySelector('[data-conference-targets]').innerHTML=targets(target.value);
    }

    async function submit(form) {
        if (form.dataset.busy==='true') return;
        const operation=form.dataset.operation;
        const fields=Object.fromEntries(new FormData(form));
        if (operation==='periodo') { competence=fields.competencia; await refresh(); return; }
        setFormBusy(form,true);
        form.dataset.busy='true';
        try {
            const values=Object.fromEntries([...form.querySelectorAll('[data-conference-value]')].map(el=>[el.dataset.conferenceValue,el.value]));
            const endpoint={vincular:'/api/conciliacao/vincular',desfazer:'/api/conciliacao/desfazer',saldos:'/api/conferencia/saldos',fechar:'/api/conferencia/fechar',reabrir:'/api/conferencia/reabrir'}[operation];
            const response=await api(endpoint,{method:'POST',body:{...fields,id:Number(form.dataset.id),entrada_id:Number(form.dataset.id),
                ids:[...form.querySelectorAll('[name=vinculo]:checked')].map(el=>Number(el.value)),valores:values,assinatura:form.dataset.hash,competencia:competence}});
            await refresh();
            showAlert('Conferência financeira', response.status==='DIVERGENTE'?`Comparação registrada com ${response.divergencias} divergência(s). Corrija os lançamentos nas telas correspondentes e faça uma nova conferência.`:'Registro concluído. O histórico foi preservado.');
        } catch (err) { form.querySelector('[data-conference-error]').textContent=err.message; }
        finally { setFormBusy(form,false); form.dataset.busy='false'; }
    }
    return {render,click,change,submit};
}

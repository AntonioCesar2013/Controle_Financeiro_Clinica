import { escapeHtml as e, formatMoney as money, localDate } from '../utils/formatters.js';
import { renderTable } from './renderers.js';

export function createWorkflows({ api, showPanel, showAlert }) {
    const field = (label, name, type = 'text', value = '') => `<div class="field"><label>${e(label)}<input name="${name}" type="${type}" value="${e(value)}" required${type === 'number' ? ' min="0.01" step="0.01"' : ''}></label></div>`;
    const hidden = (name, value) => `<input type="hidden" name="${name}" value="${e(value)}">`;
    async function open(kind, id) {
        try {
            let title, endpoint, refresh, fields;
            const today = localDate();
            if (kind === 'internment-end') {
                const i = (await api('/api/internacoes')).dados.find(r => String(r.id) === String(id));
                title = 'Conferir acerto e encerrar'; endpoint = '/api/internacoes/encerrar'; refresh = 'internacoes';
                fields = hidden('id', id) + field('Data de encerramento', 'data_encerramento', 'date', today);
                fields += i.modalidade === 'PARTICULAR' ? `<div class="field"><label>Cobranças particulares<select name="politica" required><option value="">Selecione conforme o contrato</option><option value="MANTER">Manter cobranças contratadas</option><option value="DISPENSAR_FUTURAS">Dispensar mensalidades com vencimento após a saída</option></select></label></div><p>Dispensar futuras zera essas mensalidades por inteiro. Não calcula proporcionalidade nem multa contratual.</p>` : '';
                fields += field('Motivo do encerramento', 'motivo') + `<label><input type="checkbox" name="autorizar_ajuste_desconto" value="1"> Confirmar ajustes de descontos mostrados na prévia</label>` + hidden('assinatura', '') + `<button type="button" class="button button--secondary" data-action="preview-settlement">Conferir prévia</button><div data-settlement-preview></div>`;
            } else if (kind === 'internment-extend') {
                const i = (await api('/api/internacoes')).dados.find(r => String(r.id) === String(id));
                title = 'Prorrogar internação'; endpoint = '/api/internacoes/prorrogar'; refresh = 'internacoes';
                fields = hidden('id', id) + hidden('periodo_atual', i.periodo_tratamento) + `<p>Período atual: ${e(i.periodo_tratamento)} meses. As parcelas existentes serão preservadas; as novas usam a mensalidade ou diária contratada.</p><div class="field"><label>Novo período total em meses<input name="novo_periodo" type="number" min="${Number(i.periodo_tratamento)+1}" max="120" step="1" required></label></div>` + field('Motivo', 'motivo');
            } else if (kind === 'refund' || kind === 'wallet-refund') {
                const wallet = kind === 'wallet-refund';
                title = wallet ? 'Registrar devolução da carteira' : 'Registrar devolução de recebimento';
                endpoint = wallet ? '/api/carteiras/devolver' : '/api/recebimentos/devolver'; refresh = wallet ? 'carteiras' : 'contas_receber';
                fields = `<p>Registre somente dinheiro já devolvido. O lançamento original será preservado.${wallet ? '' : ' Separe o principal das multas e juros devolvidos.'}</p>` + hidden(wallet ? 'carteira_id' : 'recebimento_id', id) + (wallet ? field('Valor devolvido', 'valor', 'number') : field('Principal devolvido', 'valor', 'number', '0').replace('min="0.01"', 'min="0"') + field('Multas e juros devolvidos', 'multa_juros', 'number', '0').replace('min="0.01"', 'min="0"')) + field('Data da devolução', wallet ? 'data_movimentacao' : 'data_devolucao', 'date', today) + field('Forma de devolução', 'forma_pagamento', 'text', 'PIX') + field('Motivo', 'motivo') + field('Comprovante / documento', 'documento');
            } else if (kind === 'refund-reversal') {
                title = 'Corrigir devolução do tratamento'; endpoint = '/api/recebimentos/devolucoes/estornar'; refresh = 'contas_receber';
                fields = `<p>Use quando a devolução foi lançada por engano. O registro original continuará no histórico.</p>${hidden('id', id)}${field('Motivo da correção', 'motivo')}`;
            } else if (kind === 'contact-primary') {
                const guardians = (await api('/api/responsaveis')).dados.filter(row => Number(row.ativo) === 1);
                title = 'Definir contato principal atual'; endpoint = '/api/residentes/contato-principal'; refresh = 'residentes';
                fields = `${hidden('residente_id', id)}<div class="field"><label>Contato principal<select name="responsavel_id" required>${guardians.map(row => `<option value="${e(row.id)}">${e(row.nome)}</option>`).join('')}</select></label></div>${field('Motivo da escolha', 'motivo')}`;
            } else if (kind === 'recurrence') {
                title = 'Programar despesa recorrente'; endpoint = '/api/recorrencias'; refresh = 'despesas';
                fields = hidden('despesa_id', id) + field('Valor de cada conta', 'valor', 'number') + field('Primeiro vencimento', 'data_inicio', 'date', today) + field('Último dia da programação', 'data_fim', 'date') + `<div class="field"><label>Intervalo em meses<input name="intervalo_meses" type="number" min="1" max="12" step="1" value="1" required></label></div><p>Depois de salvar, use “Gerar contas” na programação. O dia do primeiro vencimento será mantido; meses curtos usam o último dia.</p>`;
            } else if (kind === 'recurrence-generate') {
                title = 'Gerar contas programadas'; endpoint = '/api/recorrencias/gerar'; refresh = 'despesas';
                fields = hidden('id', id) + field('Gerar até', 'data_limite', 'date', today) + '<p>Contas já existentes na mesma data não serão duplicadas, inclusive as canceladas.</p>';
            } else return false;
            showPanel(title, `<form class="login-form maintenance-form" data-endpoint="${endpoint}" data-refresh="${refresh}" data-kind="${kind}">${fields}<p class="login-error" data-maintenance-error role="alert"></p><button class="button" type="submit">${kind === 'internment-end' ? 'Confirmar encerramento' : 'Salvar'}</button></form>`);
            return true;
        } catch (error) { showAlert('Não foi possível abrir', error.message); return true; }
    }
    async function preview(form) {
        const target = form.querySelector('[data-settlement-preview]');
        const signature = form.elements.assinatura;
        signature.value = '';
        const values = new FormData(form);
        const query = new URLSearchParams({ id: values.get('id'), data_encerramento: values.get('data_encerramento'), politica: values.get('politica') || '' });
        target.textContent = 'Consultando acerto…';
        try {
            const { dados: d } = await api(`/api/internacoes/acerto?${query}`);
            target.innerHTML = renderTable(d.cobrancas, [['Parcela', 'numero_parcela'], ['Valor anterior', 'valor_anterior', money], ['Valor após saída', 'valor_novo', money], ['Desconto anterior', 'desconto_anterior', money], ['Desconto após saída', 'desconto_novo', money], ['Recebido líquido', 'recebido', money], ['Devolver', 'devolver', money], ['Pendente', 'saldo_restante', money]]) + `<p>Devolver do tratamento: <strong>${money(d.total_devolver)}</strong>. Dívida restante: <strong>${money(d.total_pendente)}</strong>.</p><p>Saldo da carteira: <strong>${money(d.carteira?.saldo || 0)}</strong>. ${d.carteira?.saldo > 0 ? 'Registre a devolução na carteira quando realizada.' : d.carteira?.saldo < 0 ? 'Permanece uma dívida da carteira; registre o crédito ao receber.' : ''}</p>${d.total_devolver ? '<p>Faça as devoluções pelo histórico de recebimentos e consulte novamente a prévia.</p>' : ''}`;
            signature.value = d.assinatura;
        } catch (error) { target.textContent = error.message; }
    }
    return { open, preview };
}

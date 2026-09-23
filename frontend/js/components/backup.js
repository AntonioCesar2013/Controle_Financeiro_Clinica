import { escapeHtml } from '../utils/formatters.js';

export function createBackupPanel(api) {
    const esc = escapeHtml;
    let timer;
    let wasRunning = false;
    const labels = {success: '✓ Sucesso', failed: '✗ Falha', disabled: 'Desativado', skipped: 'Não enviado', pending: 'Aguardando'};
    const automaticLabels = {DESATIVADO: 'Backup automático desativado.', NUNCA_CONCLUIDO: 'Backup automático ativado, mas nenhuma cópia local íntegra foi concluída.', ATRASADO: 'Backup automático atrasado em relação ao intervalo configurado.', PARCIAL: 'Backup local em dia, mas há destino externo pendente.', EM_DIA: 'Backup automático em dia em todos os destinos ativados.'};
    function statusHtml(status) {
        const result = status.result || {};
        return `<p><strong>${esc(automaticLabels[status.automatic_state] || 'Estado do backup indisponível.')}</strong></p><p>${esc(status.message || 'Nenhum backup executado.')}</p>
            <p>Última tentativa: ${esc(status.last_attempt ? new Date(status.last_attempt).toLocaleString('pt-BR') : '—')}<br>
            Último snapshot local íntegro: ${esc(status.last_success ? new Date(status.last_success).toLocaleString('pt-BR') : '—')}<br>
            Próxima execução esperada: ${esc(status.next_due ? new Date(status.next_due).toLocaleString('pt-BR') : '—')}</p>
            <p>Arquivo: ${esc(result.filename || '—')} · ${result.size ? (result.size / 1048576).toFixed(2) + ' MB' : '—'} · ${esc(String(result.duration_seconds ?? '—'))} s</p>
            <p>Local: ${labels[result.local] || '—'}<br>Cloudflare R2: ${labels[result.r2] || '—'} · último envio: ${esc(status.last_r2_success ? new Date(status.last_r2_success).toLocaleString('pt-BR') : '—')}<br>Google Drive: ${labels[result.drive] || '—'} · último envio: ${esc(status.last_drive_success ? new Date(status.last_drive_success).toLocaleString('pt-BR') : '—')}</p>
            ${(result.errors || []).map(error => `<p class="form-note">${esc(error)}</p>`).join('')}
            <p>${esc(status.status_warning || status.scheduler_warning || '')}</p>`;
    }
    async function poll() {
        clearTimeout(timer);
        const container = document.querySelector('#backup-status');
        if (!container) return;
        try {
            const status = await api('/api/backup/status');
            container.innerHTML = statusHtml(status);
            if (wasRunning && !status.running) {
                const settings = await api('/api/backup/config');
                const folder = document.querySelector('[data-backup-config="drive_folder_id"]');
                if (folder && !folder.value) folder.value = settings.config.drive_folder_id;
                const account = document.querySelector('#backup-drive-account');
                if (account) account.textContent = settings.configured.drive_token ? 'Conta conectada (teste para validar).' : 'Conta desconectada.';
            }
            wasRunning = Boolean(status.running);
            document.querySelectorAll('[data-backup-action]').forEach(button => button.disabled = status.running);
            const root = document.querySelector('#backup-panel');
            if (root) root.setAttribute('aria-busy', String(Boolean(status.running)));
        } catch (error) { container.textContent = error.message; }
        timer = setTimeout(poll, 2500);
    }
    async function render() {
        clearTimeout(timer);
        let settings;
        try { settings = await api('/api/backup/config'); }
        catch (error) { return `<h3>Backup do sistema</h3><p>${esc(error.message)}</p>`; }
        const c = settings.config, configured = settings.configured;
        const field = (name, label, type = 'text') => `<label>${label}<input data-backup-config="${name}" type="${type}" value="${esc(String(c[name]))}" ${type === 'number' ? 'min="0.01" max="8760" step="0.01"' : ''}></label>`;
        const check = (name, label) => `<label><input type="checkbox" data-backup-config="${name}" ${c[name] ? 'checked' : ''}> ${label}</label>`;
        const secret = (name, label) => `<label>${label}<input type="password" autocomplete="new-password" data-backup-secret="${name}" placeholder="${configured[name] ? '******** configurado (vazio mantém)' : 'Não configurado'}"></label>`;
        const button = (action, label) => `<button type="button" class="button" data-backup-action="${action}">${label}</button>`;
        timer = setTimeout(poll, 100);
        return `<section id="backup-panel"><h3 class="section-title">Backup do sistema</h3>
            <p class="form-note">Configuração disponível somente no acesso local deste computador.</p>
            <p class="form-note">${esc(settings.warning)}</p>
            <div class="form-grid">${check('backup_enabled', 'Backup automático ativado')}${field('interval_hours', 'Intervalo (horas)', 'number')}
            ${field('backup_directory', 'Pasta local (caminho absoluto)')}</div>${button('folder', 'Selecionar pasta')}
            <h3 class="section-title">Cloudflare R2</h3><div class="form-grid">${check('r2_enabled', 'R2 ativado')}
            ${field('r2_bucket', 'Bucket')}${field('r2_endpoint', 'Endpoint HTTPS')}${field('r2_prefix', 'Prefixo')}
            ${secret('r2_access_key_id', 'Access Key')}${secret('r2_secret_access_key', 'Secret Key')}</div>${button('test-r2', 'Testar R2')}
            <h3 class="section-title">Google Drive</h3><p id="backup-drive-account">Conta: ${configured.drive_token ? 'Conectada (token armazenado; teste para validar)' : 'Desconectada'}</p>
            <div class="form-grid">${check('drive_enabled', 'Drive ativado')}${field('drive_client_id', 'Client ID OAuth Desktop')}
            ${secret('drive_client_secret', 'Client Secret OAuth')}${field('drive_folder_id', 'ID da pasta (vazio cria pasta padrão)')}</div>
            <p class="form-note">O consentimento abre no navegador deste computador. Use uma pasta criada pelo aplicativo; pastas externas precisam ser autorizadas ao aplicativo no Google.</p>
            <div class="report-actions">${button('connect', 'Conectar Google Drive')}${button('disconnect', 'Desconectar')}${button('test-drive', 'Testar Drive')}</div>
            <h3 class="section-title">Status</h3><div id="backup-status" role="status" aria-live="polite">${statusHtml(settings.status)}</div>
            <div class="report-actions">${button('save', 'Salvar configurações')}${button('backup', 'Executar backup agora')}</div></section>`;
    }
    async function handle(event) {
        const button = event.target.closest('[data-backup-action]');
        if (!button) return;
        event.preventDefault();
        button.disabled = true;
        const output = document.querySelector('#backup-status');
        try {
            const action = button.dataset.backupAction;
            if (action === 'folder') {
                const result = await api('/api/backup/folder', {method: 'POST', body: {}});
                if (result.directory) document.querySelector('[data-backup-config="backup_directory"]').value = result.directory;
                return;
            }
            if (action !== 'disconnect') {
                const config = {}, credentials = {};
                document.querySelectorAll('[data-backup-config]').forEach(input => {
                    config[input.dataset.backupConfig] = input.type === 'checkbox' ? input.checked : input.type === 'number' ? Number(input.value) : input.value.trim();
                });
                document.querySelectorAll('[data-backup-secret]').forEach(input => {
                    if (input.value) credentials[input.dataset.backupSecret] = input.value;
                    input.value = '';
                });
                const saved = await api('/api/backup/config', {method: 'POST', body: {config, credentials}});
                document.querySelectorAll('[data-backup-secret]').forEach(input => {
                    input.placeholder = saved.configured[input.dataset.backupSecret] ? '******** configurado (vazio mantém)' : 'Não configurado';
                });
                for (const key of Object.keys(credentials)) delete credentials[key];
            }
            if (action === 'save') output.textContent = 'Configurações salvas.';
            else {
                await api('/api/backup/' + action, {method: 'POST', body: {}});
                wasRunning = true;
                output.textContent = action === 'connect' ? 'Conclua o consentimento no navegador. Limite: 3 minutos.' : 'Operação iniciada.';
                timer = setTimeout(poll, 1000);
            }
        } catch (error) { output.textContent = error.message; }
        finally { button.disabled = false; }
    }
    document.addEventListener('click', handle);
    return {render};
}

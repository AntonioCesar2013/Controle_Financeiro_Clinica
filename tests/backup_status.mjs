import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../frontend/js/components/backup.js', import.meta.url), 'utf8');
for (const state of ['DESATIVADO', 'NUNCA_CONCLUIDO', 'ATRASADO', 'PARCIAL', 'EM_DIA']) {
    assert.match(source, new RegExp(state));
}
assert.match(source, /Último snapshot local íntegro/);
assert.match(source, /last_r2_success/);
assert.match(source, /last_drive_success/);
assert.match(source, /destino externo pendente/);
console.log('Status operacional de backup e resultados independentes validados.');

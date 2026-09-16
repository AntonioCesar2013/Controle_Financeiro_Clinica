import assert from 'node:assert/strict';
import { parametrosContasPagar, despesasElegiveis } from '../frontend/js/components/contas-pagar.js';

const estado = {pagina: 2, busca: 'Água', status: 'ABERTA', inicio: '2026-02-01', fim: '2026-02-28', ordem: 'vencimento_desc'};
const parametros = parametrosContasPagar(estado);
assert.equal(parametros.get('data_inicio'), estado.inicio);
assert.equal(parametros.get('data_fim'), estado.fim);
assert.equal(parametros.get('inicio'), null);
assert.equal(parametros.get('pagina'), '2');
assert.equal(parametros.get('status'), 'ABERTA');
assert.equal(parametros.get('busca'), 'Água');
assert.equal(parametrosContasPagar({...estado, inicio: '', fim: ''}).get('data_inicio'), '');

const registros = {setores: [{id: 1, ativo: 0}, {id: 2, ativo: 1}], despesas: [
    {id: 1, setor_id: 1, ativo: 1}, {id: 2, setor_id: 2, ativo: 1}, {id: 3, setor_id: 2, ativo: 0},
]};
assert.deepEqual(despesasElegiveis(registros).map(item => item.id), [2]);
assert.deepEqual(despesasElegiveis({...registros, setores: [{id: 1, ativo: 0}, {id: 2, ativo: 0}]}), []);
console.log('Contas a pagar: contrato de filtros e despesas elegíveis validados.');
if (process.argv.includes('--query')) {
    console.log(parametrosContasPagar({pagina: 1, busca: 'agua', status: 'ABERTA',
        inicio: '2026-02-01', fim: '2026-02-28', ordem: 'vencimento_asc'}).toString());
}

import assert from 'node:assert/strict';
import { groupInternmentPeople, internmentPeopleOptions, internmentContractTotal, internmentMoneyPayload } from '../frontend/js/components/internment-form.js';
import { prepararInternacao } from '../frontend/js/components/cadastros.js';

const people = [{id: 1, nome: 'Álvaro', cpf: '12345678900'}, {id: 2, nome: 'Zélia'}, {id: 3, nome: '<Ana>'}];
const internments = [{residente_id: 1, responsavel_id: 2, status: 'ATIVA'},
    {residente_id: 2, responsavel_id: 3, status: 'ENCERRADA'},
    {residente_id: 3, responsavel_id: 1, status: 'AGENDADA'}];
const residentGroups = groupInternmentPeople(people, internments, 'residente_id');
assert.deepEqual(residentGroups.map(g => g.map(p => p.id)), [[3, 2], [1]]);
assert.deepEqual(groupInternmentPeople(people, internments, 'responsavel_id').map(g => g.map(p => p.id)), [[3, 1], [2]]);
assert.equal(groupInternmentPeople(people, internments, 'residente_id', 'alvaro')[1][0].id, 1);
assert.equal(groupInternmentPeople(people, internments, 'residente_id', '123.456.789-00')[1][0].id, 1);
assert.equal(groupInternmentPeople(people, internments, 'residente_id', 'inexistente').flat().length, 0);
const options = internmentPeopleOptions(residentGroups, 1);
assert.match(options, /value="1" selected/);
assert.match(options, /&lt;Ana&gt;/);
assert.ok(options.indexOf('Zélia') < options.indexOf('────────'));
assert.ok(options.indexOf('────────') < options.indexOf('Álvaro'));
const total = internmentContractTotal('R$ 1.000,50', 'R$ 250,25', '3');
assert.equal(total.replace(/\s/g, ''), 'R$1.751,25');
const payload = prepararInternacao(internmentMoneyPayload({modalidade: 'PARTICULAR', valor_contrato: total,
    valor_acolhimento: 'R$ 1.000,50', valor_mensalidade: 'R$ 250,25'}));
assert.equal(payload.valor_contrato, '1751.25');
assert.equal(payload.valor_acolhimento, '1000.50');
assert.equal(payload.valor_mensalidade, '250.25');
assert.equal(prepararInternacao(internmentMoneyPayload({modalidade: 'VOLUNTARIO'})).valor_contrato, 0);
console.log('Internação: grupos, pesquisa, seleção preservada, escape, cálculo e envio monetário aprovados.');

import assert from 'node:assert/strict';
import { responsaveisElegiveis, opcoesResponsavelContratual, prepararInternacao, criarPessoa } from '../frontend/js/components/cadastros.js';
import { applyInputMask } from '../frontend/js/utils/masks.js';
import { readFile } from 'node:fs/promises';

const responsaveis = [
    {id: 1, nome: 'Ana', ativo: 1},
    {id: 2, nome: 'Bruno', ativo: 1},
    {id: 3, nome: 'Caio', ativo: 0},
];
assert.deepEqual(responsaveisElegiveis(responsaveis).map(item => item.id), [1, 2]);
assert.deepEqual(responsaveisElegiveis([{id: 3, ativo: 0}]), []);
const atual = opcoesResponsavelContratual({responsavel_id: 2}, responsaveis);
assert.match(atual.opcoes, /value="2" selected/);
assert.doesNotMatch(atual.opcoes, /value="1" selected/);
const inativo = opcoesResponsavelContratual({responsavel_id: 3}, responsaveis);
assert.match(inativo.opcoes, /value="3" selected/);
assert.match(inativo.aviso, /inativo/);

const voluntario = prepararInternacao({modalidade: 'VOLUNTARIO', periodo_tratamento: '', convenio_id: '5', valor_contrato: '99', servicos_voluntario: 'Apoio'});
assert.equal(voluntario.periodo_tratamento, 0);
assert.equal(voluntario.convenio_id, null);
assert.equal(voluntario.valor_contrato, 0);
assert.equal(voluntario.servicos_voluntario, 'Apoio');
const social = prepararInternacao({modalidade: 'SOCIAL', periodo_tratamento: '2', servicos_voluntario: 'oculto'});
assert.equal(social.periodo_tratamento, '2');
assert.equal('servicos_voluntario' in social, false);

const chamadas = [];
const duplicado = await criarPessoa(async (rota, opcoes) => {
    chamadas.push([rota, opcoes]);
    return {sucesso: true, existe: true, id: 8, nome: 'Original'};
}, '/api/residentes', {nome: 'Não gravar', cpf: '123'});
assert.equal(duplicado.criada, false);
assert.equal(duplicado.id, 8);
assert.match(duplicado.mensagem, /não foram gravados/);
assert.equal(chamadas.length, 1);
assert.equal((await criarPessoa(async () => ({sucesso: true, existe: false, id: 9}), '/api/responsaveis', {})).criada, true);

const appSource = await readFile(new URL('../frontend/js/app.js', import.meta.url), 'utf8');
assert.match(appSource, /Ações do responsável selecionado/);
assert.match(appSource, /data-kind="guardian" data-selection-action="edit" disabled>Editar/);

const pendente = {value: 'PENDENTE-TESTE', dataset: {}};
applyInputMask(pendente);
assert.equal(pendente.value, 'PENDENTE-TESTE');
console.log('Cadastros: seleção contratual, elegibilidade, voluntário, duplicidade e identificador pendente validados.');

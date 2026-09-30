import assert from 'node:assert/strict';
import { uppercaseInput } from '../frontend/js/utils/uppercase.js';
const input = (value, name='nome', type='text', preserve=false) => ({
    value, name, type, tagName:'INPUT', selectionStart:2, selectionEnd:2, selectionDirection:'none',
    matches: selector => selector === 'input, textarea' || preserve,
    setSelectionRange(start, end) { this.cursor = [start, end]; },
});
const name = input('joão da ação');
uppercaseInput(name);
assert.equal(name.value, 'JOÃO DA AÇÃO');
assert.deepEqual(name.cursor, [2,2]);
for (const field of [input('SenhaAbc', 'senha', 'password'), input('Pessoa@Email.com', 'email', 'email'),
    input('Abc/Chave', '', 'text', true), input('abc123', 'assinatura', 'hidden')]) {
    const original = field.value;
    uppercaseInput(field);
    assert.equal(field.value, original);
}
const search = input('josé', '', 'search');
uppercaseInput(search);
assert.equal(search.value, 'JOSÉ');
console.log('Maiúsculas: acentos, cursor, pesquisa e exceções aprovados.');

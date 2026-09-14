import assert from 'node:assert/strict';
import { createApi, UnknownOperationError } from '../frontend/js/core/api.js';

const response = (status, payload) => ({
    status, ok: status >= 200 && status < 300,
    async json() { return payload; },
});

{
    const calls = [];
    globalThis.fetch = async (url, options) => {
        calls.push({url, options});
        return response(201, {sucesso: true, estado_operacao: 'CONFIRMADA'});
    };
    const api = createApi();
    await api('/api/residentes', {method: 'POST', body: {nome: 'Teste', cpf: '1'}});
    assert.match(calls[0].options.headers['Idempotency-Key'], /^[A-Za-z0-9_-]{16,128}$/);
}

{
    let release;
    const waiting = new Promise(resolve => { release = resolve; });
    let posts = 0;
    globalThis.fetch = async () => {
        posts += 1;
        await waiting;
        return response(200, {sucesso: true, id: 7});
    };
    const api = createApi();
    const first = api('/api/carteiras/credito', {method: 'POST', body: {carteira_id: 1, valor: '10.00'}});
    const second = api('/api/carteiras/credito', {method: 'POST', body: {valor: '10.00', carteira_id: 1}});
    release();
    assert.deepEqual(await Promise.all([first, second]), [{sucesso: true, id: 7}, {sucesso: true, id: 7}]);
    assert.equal(posts, 1, 'cliques repetidos devem compartilhar a mesma operação');
}

{
    const bodies = new Map();
    globalThis.fetch = async (_url, options) => {
        const key = options.headers['Idempotency-Key'];
        const body = options.body;
        if (bodies.has(key) && bodies.get(key) !== body) {
            return response(409, {erro: 'O identificador já foi usado com outros dados.'});
        }
        bodies.set(key, body);
        return response(200, {sucesso: true});
    };
    const api = createApi();
    const key = 'operacao_reutilizada_123';
    await api('/api/carteiras/credito', {method: 'POST', body: {valor: 10}, operationKey: key});
    await assert.rejects(
        api('/api/carteiras/credito', {method: 'POST', body: {valor: 20}, operationKey: key}),
        /outros dados/,
    );
}

{
    let operationKey;
    globalThis.fetch = async (url, options = {}) => {
        if (url === '/api/residentes') {
            operationKey = options.headers['Idempotency-Key'];
            throw new TypeError('resposta perdida');
        }
        if (String(url).startsWith('/api/operacoes/status')) {
            return response(200, {dados: {estado: 'CONFIRMADA', resultado: {sucesso: true, id: 42}}});
        }
        throw new Error('chamada inesperada');
    };
    const api = createApi();
    assert.deepEqual(await api('/api/residentes', {method: 'POST', body: {nome: 'Resposta perdida'}}), {sucesso: true, id: 42});
    assert.ok(operationKey);
}

{
    const keys = [];
    let attempt = 0;
    globalThis.fetch = async (url, options = {}) => {
        if (url === '/api/carteiras/credito') {
            keys.push(options.headers['Idempotency-Key']);
            if (attempt++ === 0) throw new TypeError('sem resposta');
            return response(200, {sucesso: true});
        }
        if (String(url).startsWith('/api/operacoes/status')) throw new TypeError('sem conexão para consultar');
        throw new Error('chamada inesperada');
    };
    const api = createApi();
    const body = {carteira_id: 1, valor: '5.00'};
    await assert.rejects(api('/api/carteiras/credito', {method: 'POST', body}), UnknownOperationError);
    await api('/api/carteiras/credito', {method: 'POST', body});
    assert.equal(keys[0], keys[1], 'resultado desconhecido deve reutilizar a chave original');
}

{
    let cancelled = false;
    globalThis.fetch = async (url) => {
        if (url === '/api/carteiras/credito') throw new TypeError('sem resposta');
        if (String(url).startsWith('/api/operacoes/status')) {
            return response(200, {dados: {estado: 'NAO_LOCALIZADA'}});
        }
        if (url === '/api/operacoes/cancelar') {
            cancelled = true;
            return response(200, {sucesso: true, estado: 'CANCELADA'});
        }
        throw new Error('chamada inesperada');
    };
    const api = createApi();
    await assert.rejects(
        api('/api/carteiras/credito', {method: 'POST', body: {carteira_id: 1, valor: 5}}),
        /não foi realizada/,
    );
    assert.equal(cancelled, true);
}

console.log('Cliente de gravações: chave, reenvio, recuperação e cancelamento seguro validados.');

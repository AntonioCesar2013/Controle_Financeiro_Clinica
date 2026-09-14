import { createApi } from '../../frontend/js/core/api.js';

const base = process.argv[2];
const nativeFetch = globalThis.fetch;
let discardFirstResponse = true;
let sentKey = null;
globalThis.fetch = async (url, options = {}) => {
    const absolute = new URL(url, base).href;
    if (url === '/api/responsaveis' && discardFirstResponse) {
        discardFirstResponse = false;
        sentKey = options.headers['Idempotency-Key'];
        await nativeFetch(absolute, options);
        throw new TypeError('resposta descartada pelo teste');
    }
    return nativeFetch(absolute, options);
};

const api = createApi();
const result = await api('/api/responsaveis', {
    method: 'POST',
    body: {nome: 'Cliente JavaScript real', cpf: '45678901234'},
});
process.stdout.write(JSON.stringify({result, sentKey}));

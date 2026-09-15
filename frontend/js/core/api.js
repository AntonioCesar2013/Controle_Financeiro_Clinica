const OWN_POST_ROUTES = ["/api/auth/", "/api/backup/", "/api/sincronizacao/"];

export class UnknownOperationError extends Error {
    constructor(operationKey) {
        super("O servidor pode ter concluído a operação, mas a resposta não chegou. Tente novamente sem alterar os dados para consultar o mesmo resultado.");
        this.name = "UnknownOperationError";
        this.operationKey = operationKey;
        this.operationState = "DESCONHECIDA";
    }
}

function stable(value) {
    if (Array.isArray(value)) return value.map(stable);
    if (value && typeof value === "object") {
        return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
    }
    return value;
}

function newOperationKey() {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID().replaceAll("-", "");
    const random = Array.from({ length: 4 }, () => Math.random().toString(36).slice(2)).join("");
    return `${Date.now().toString(36)}_${random}`.slice(0, 128).padEnd(16, "0");
}

function isBusinessPost(url, method) {
    const path = new URL(url, "http://localhost").pathname;
    return method === "POST" && path.startsWith("/api/")
        && path !== "/api/operacoes/cancelar"
        && !OWN_POST_ROUTES.some((prefix) => path.startsWith(prefix));
}

async function readResponse(response) {
    const payload = await response.json().catch(() => ({}));
    return { response, payload };
}

export function createApi({ onUnauthorized } = {}) {
    const pending = new Map();
    const running = new Map();
    const runningGets = new Map();

    async function fetchJson(url, options = {}, operationKey) {
        const headers = options.body ? { "Content-Type": "application/json" } : {};
        if (operationKey) headers["Idempotency-Key"] = operationKey;
        return readResponse(await fetch(url, {
            method: options.method || "GET",
            headers,
            body: options.body ? JSON.stringify(options.body) : undefined,
            credentials: "same-origin",
            signal: options.signal,
        }));
    }

    async function operationStatus(operationKey) {
        const { response, payload } = await fetchJson(
            `/api/operacoes/status?chave=${encodeURIComponent(operationKey)}`,
        );
        if (!response.ok) throw new Error(payload.erro || "Não foi possível consultar a operação.");
        return payload.dados;
    }

    async function cancelOperation(operationKey) {
        const { response, payload } = await fetchJson("/api/operacoes/cancelar", {
            method: "POST", body: { chave: operationKey },
        });
        if (!response.ok) throw new Error(payload.erro || "Não foi possível cancelar a tentativa.");
        return payload;
    }

    async function recover(operationKey, fingerprint, waitWasCancelled = false) {
        try {
            const status = await operationStatus(operationKey);
            if (status.estado === "CONFIRMADA") {
                pending.delete(fingerprint);
                return status.resultado;
            }
            if (status.estado === "CANCELADA") {
                pending.delete(fingerprint);
                throw new Error("A operação não foi realizada; a tentativa foi cancelada com segurança.");
            }
            if (!waitWasCancelled && status.estado === "NAO_LOCALIZADA") {
                const cancelled = await cancelOperation(operationKey);
                if (cancelled.estado === "CONFIRMADA") {
                    pending.delete(fingerprint);
                    return cancelled.resultado;
                }
                if (cancelled.estado === "CANCELADA") {
                    pending.delete(fingerprint);
                    throw new Error("A operação não foi realizada. A tentativa sem resposta foi cancelada com segurança.");
                }
            }
        } catch (error) {
            if (!/não foi realizada/.test(error?.message || "")) throw new UnknownOperationError(operationKey);
            throw error;
        }
        throw new UnknownOperationError(operationKey);
    }

    async function perform(url, options, operationKey, fingerprint) {
        let result;
        try {
            result = await fetchJson(url, options, operationKey);
        } catch (error) {
            return recover(operationKey, fingerprint, error?.name === "AbortError");
        }
        const { response, payload } = result;
        if (response.status === 401 && !options.allowUnauthorized) {
            pending.delete(fingerprint);
            onUnauthorized?.("Sua sessão expirou. Entre novamente.");
            throw new Error("Sessão expirada.");
        }
        if (response.status === 404 && payload.erro === "Rota não encontrada.") {
            pending.delete(fingerprint);
            throw new Error("O servidor está executando uma versão anterior. Encerre o Python e inicie o sistema novamente.");
        }
        if (!response.ok && payload.estado_operacao === "VERIFICAR") {
            return recover(operationKey, fingerprint);
        }
        pending.delete(fingerprint);
        if (!response.ok) throw new Error(payload.erro || "Não foi possível concluir a operação.");
        return payload;
    }

    async function api(url, options = {}) {
        const method = (options.method || "GET").toUpperCase();
        if (!isBusinessPost(url, method)) {
            const chaveGet = method === "GET" && !options.signal ? String(url) : null;
            if (chaveGet && runningGets.has(chaveGet)) return runningGets.get(chaveGet);
            const leitura = (async () => {
                const { response, payload } = await fetchJson(url, options);
                if (response.status === 401 && !options.allowUnauthorized) {
                    onUnauthorized?.("Sua sessão expirou. Entre novamente.");
                    throw new Error("Sessão expirada.");
                }
                if (response.status === 404 && payload.erro === "Rota não encontrada.") {
                    throw new Error("O servidor está executando uma versão anterior. Encerre o Python e inicie o sistema novamente.");
                }
                if (!response.ok) throw new Error(payload.erro || "Não foi possível concluir a operação.");
                return payload;
            })();
            if (!chaveGet) return leitura;
            runningGets.set(chaveGet, leitura);
            return leitura.finally(() => runningGets.delete(chaveGet));
        }

        const fingerprint = JSON.stringify(stable([new URL(url, "http://localhost").pathname, options.body ?? null]));
        const operationKey = options.operationKey || pending.get(fingerprint) || newOperationKey();
        pending.set(fingerprint, operationKey);
        if (running.has(fingerprint)) return running.get(fingerprint);
        const promise = perform(url, options, operationKey, fingerprint).finally(() => running.delete(fingerprint));
        running.set(fingerprint, promise);
        return promise;
    }

    api.operationStatus = operationStatus;
    api.cancelOperation = cancelOperation;
    api.pendingOperation = (url, body) => pending.get(JSON.stringify(stable([
        new URL(url, "http://localhost").pathname, body ?? null,
    ]))) || null;
    return api;
}

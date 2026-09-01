export function createApi({ onUnauthorized }) {
    return async function api(url, options = {}) {
        const response = await fetch(url, {
            method: options.method || "GET",
            headers: options.body ? { "Content-Type": "application/json" } : {},
            body: options.body ? JSON.stringify(options.body) : undefined,
            credentials: "same-origin",
        });

        const payload = await response.json().catch(() => ({}));

        if (response.status === 401 && !options.allowUnauthorized) {
            onUnauthorized?.("Sua sessão expirou. Entre novamente.");
            throw new Error("Sessão expirada.");
        }

        if (response.status === 404 && payload.erro === "Rota não encontrada.") {
            throw new Error("O servidor está executando uma versão anterior. Encerre o Python e inicie o sistema novamente.");
        }

        if (!response.ok) {
            throw new Error(payload.erro || "Não foi possível concluir a operação.");
        }

        return payload;
    };
}

// Contrato de filtros e elegibilidade do formulário de contas a pagar.

export function parametrosContasPagar(estado) {
    return new URLSearchParams({
        pagina: String(estado.pagina), tamanho: "50",
        busca: estado.busca || "", status: estado.status || "",
        data_inicio: estado.inicio || "", data_fim: estado.fim || "",
        ordem: estado.ordem || "vencimento_asc",
    });
}

export function despesasElegiveis(registros) {
    const setoresAtivos = new Set(registros.setores.filter(item => Number(item.ativo) === 1).map(item => String(item.id)));
    return registros.despesas.filter(item => Number(item.ativo) === 1 && setoresAtivos.has(String(item.setor_id)));
}

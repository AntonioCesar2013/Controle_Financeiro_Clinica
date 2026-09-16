import { escapeHtml } from "../utils/formatters.js";

export function responsaveisElegiveis(responsaveis) {
    return responsaveis.filter(item => Number(item.ativo) === 1);
}

export function opcoesResponsavelContratual(internacao, responsaveis) {
    if (!internacao) throw new Error("Internação não encontrada.");
    const atual = responsaveis.find(item => String(item.id) === String(internacao.responsavel_id));
    if (!atual) throw new Error("Responsável contratual atual não encontrado.");
    const ativos = responsaveisElegiveis(responsaveis);
    const aviso = Number(atual.ativo) === 1 ? "" : "O responsável contratual atual está inativo. Selecione explicitamente outro responsável ativo para substituí-lo.";
    const opcoes = [atual, ...ativos.filter(item => String(item.id) !== String(atual.id))];
    return { aviso, opcoes: opcoes.map(item => `<option value="${escapeHtml(item.id)}"${String(item.id) === String(atual.id) ? " selected" : ""}>${escapeHtml(item.nome)}${Number(item.ativo) === 1 ? "" : " (atual, inativo)"}</option>`).join("") };
}

export function prepararInternacao(dados) {
    const payload = { ...dados };
    if (payload.modalidade === "VOLUNTARIO") {
        payload.periodo_tratamento = 0;
        payload.convenio_id = null;
        payload.valor_contrato = 0;
        payload.valor_acolhimento = 0;
        payload.valor_mensalidade = 0;
    } else {
        delete payload.servicos_voluntario;
        if (payload.modalidade !== "CONVENIO") delete payload.convenio_id;
        if (payload.modalidade !== "PARTICULAR") {
            payload.valor_contrato = 0;
            payload.valor_acolhimento = 0;
            payload.valor_mensalidade = 0;
        }
    }
    return payload;
}

export async function criarPessoa(api, rota, dados) {
    const resposta = await api(rota, { method: "POST", body: dados });
    return resposta.existe
        ? { criada: false, id: resposta.id, mensagem: "Este documento já pertence a um cadastro existente. Os dados digitados não foram gravados. Abra a edição para alterá-lo." }
        : { criada: true, id: resposta.id };
}

export const cadastrosModule = {
    name: "cadastros",
    panels: (r) => ({
        residentes: ["Residentes", "Cadastro e consulta", r.renderResidents],
        responsaveis: ["Responsáveis", "Cadastro e consulta", r.renderGuardians],
        internacoes: ["Internações", "Acompanhamento", r.renderInternments],
        colaboradores: ["Colaboradores", "Acesso e equipe", r.renderCollaborators],
    }),
};

export const administracaoModule = {
    name: "administracao",
    panels: (r) => ({
        itens_administracao: ["Itens administrativos", "Inventário, transferências e baixas", r.renderAdministrationItems],
    }),
};

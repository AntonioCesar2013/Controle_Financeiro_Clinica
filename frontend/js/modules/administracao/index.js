export const administracaoModule = {
    name: "administracao",
    panels: (r) => ({
        itens_administracao: ["Itens administrativos", "Inventário, transferências e baixas", r.renderAdministrationItems],
        importacoes: ["Importar arquivos", "Importação validada de dados em CSV", r.renderImports],
    }),
};

export const cantinaModule = {
    name: "cantina",
    panels: (r) => ({
        carteiras: ["Carteiras", "Saldo e compras dos residentes", r.renderWallets],
        cantina: ["Cantina", "Mercadinho dos residentes", r.renderCantina],
        itens: ["Produtos da Cantina", "Catálogo, preços e estoque", r.renderProducts],
    }),
};

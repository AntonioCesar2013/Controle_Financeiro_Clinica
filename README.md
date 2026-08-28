# Controle_Financeiro_Clinica
Sistema de controle financeiro de clinica de recuperacao

## Executar a aplicação

### Windows — modo recomendado

Dê dois cliques em `iniciar.cmd`.

O iniciador localiza o Python instalado, prepara as tabelas necessárias e abre
o sistema no navegador padrão.

### Terminal

Na raiz do projeto, também é possível executar:

```powershell
python main.py
```

O navegador será aberto automaticamente em `http://127.0.0.1:8000`.

No primeiro acesso, o sistema solicitará o cadastro do primeiro colaborador.
Nos acessos seguintes, utilize o CPF e a senha cadastrados.

O frontend deve ser aberto pelo servidor. A abertura direta de
`frontend/index.html` não possui acesso à API Python.

## Primeira execução

1. Inicie o sistema por `iniciar.cmd` ou `python main.py`.

Para substituir os dados de demonstração pelas despesas reais conferidas nos
relatórios de agosto de 2026, execute `python -m src.popular_despesas_reais`.
O processo cria automaticamente uma cópia de segurança do banco antes da troca.

Quando a forma de um pagamento ou recebimento não for informada, o sistema usa
`PIX` como padrão.

As entradas bancárias reais do relatório Cora de agosto de 2026 podem ser
recarregadas com `python -m src.popular_entradas_reais`.

## Cantina

A Cantina funciona como um mercadinho interno. Cada venda usa o preço vigente
do item e desconta imediatamente o total da carteira do residente. O sistema
impede compras sem saldo e mantém no histórico o produto, a quantidade e o
preço utilizado na operação.

O cadastro de produtos reúne nome, código de barras, descrição, categoria,
unidade de medida, preço vigente, estoque inicial, estoque mínimo e status. As
vendas baixam o estoque automaticamente e são recusadas quando não há unidades
suficientes.

## Relatórios

O módulo Relatórios permite visualizar e imprimir em papel A4 os controles de
Financeiro, Despesas por setor, Internações, Residentes, Cantina, Carteiras,
Estoque e Colaboradores. Relatórios com movimentação aceitam período inicial e
final antes da visualização.

## Regra de atividade dos residentes

Todo residente é cadastrado inicialmente como inativo. O sistema marca o
residente como ativo somente quando a data atual estiver entre o acolhimento e
o término do período contratado de uma internação. Internações futuras ou
encerradas mantêm o residente inativo.
2. Informe nome, CPF e uma senha com pelo menos 8 caracteres.
3. Esse cadastro será o primeiro colaborador com acesso ao sistema.
4. Nos próximos acessos, use o mesmo CPF e senha.

O arquivo local `dados/clinica.db` é criado automaticamente e não é enviado ao
Git, pois cada instalação deve possuir seu próprio banco.

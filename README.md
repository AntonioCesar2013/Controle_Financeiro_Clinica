# Controle_Financeiro_Clinica
Sistema de controle financeiro de clinica de recuperacao

## Organização do backend

O código Python está separado por responsabilidade:

```text
src/
├── infraestrutura/  # Banco, backups, auditoria, configuração e sincronização
├── cadastros/       # Residentes, responsáveis, colaboradores, convênios e internações
├── financeiro/      # Cobranças, parcelas, contas, pagamentos, recebimentos e caixa
├── cantina/         # vendas.py: caixa/carteiras; produtos.py: catálogo e estoque
├── interface/       # Servidor HTTP, consultas para o frontend e relatórios
├── scripts/         # Populadores fictícios e importadores de dados reais
└── test.py          # Teste manual existente (altera dados; não executar em produção)
```

Novos módulos devem importar diretamente dos pacotes, por exemplo:
`from src.infraestrutura.banco import conectar`. Os `__init__.py` não executam
inicialização do banco nem importam antecipadamente os módulos dos pacotes.

`main.py` continua sendo a entrada da aplicação WebView2. Também continuam
funcionando `python -m src.servidor`, `python -m src.banco`,
`python -m src.backup_banco` e os três comandos `src.popular_*`, por meio de
arquivos pequenos de compatibilidade na raiz de `src`. Os mesmos arquivos
podem ser executados diretamente pelo VS Code. A implementação deve ser
alterada dentro dos pacotes, não nesses arquivos de entrada.

Os dados permanecem em `dados/clinica.db`, o frontend em `frontend/` e a
configuração local na raiz do projeto. A reorganização não move o banco.

## Executar a aplicação

### Windows — modo recomendado

Dê dois cliques em `iniciar.cmd`.

O iniciador localiza o Python instalado, prepara as tabelas necessárias e abre
o sistema em sua janela WebView2, sem abrir o navegador padrão.

### Terminal

Na raiz do projeto, também é possível executar:

```powershell
python main.py
```

O sistema será aberto em uma janela própria baseada no Microsoft Edge WebView2.
O servidor local é iniciado em segundo plano e encerrado automaticamente quando
a janela for fechada. O navegador comum não é aberto.

No primeiro acesso, o sistema solicitará o cadastro do primeiro colaborador.
Nos acessos seguintes, utilize o CPF e a senha cadastrados.

O frontend deve ser aberto pelo servidor. A abertura direta de
`frontend/index.html` não possui acesso à API Python.

## Primeira execução

1. Inicie o sistema por `iniciar.cmd` ou `python main.py`.

Para preparar uma instalação exclusivamente para demonstração e testes, execute:

```powershell
python -m src.popular_banco
```

Esse comando cria um backup do banco atual, remove os dados existentes e popula
todas as tabelas com um cenário fictício completo. O acesso de demonstração é
CPF `90000000001` e senha `admin1234`. Não execute o populador fictício sobre
uma instalação em produção sem a intenção de substituir seus dados.

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

O caixa aceita leitores de código de barras configurados no modo teclado: basta
manter o campo de leitura selecionado e ler o produto. O Enter enviado pelo
leitor adiciona o item ao carrinho; leituras repetidas aumentam a quantidade.
Também é possível adicionar produtos manualmente, conferir saldo e total e
finalizar todos os itens em um único cupom. O estorno é feito pelo cupom inteiro,
devolvendo o saldo à carteira e as quantidades ao estoque na mesma operação.

O cadastro de produtos reúne nome, código de barras, descrição, categoria,
unidade de medida, preço vigente, estoque inicial, estoque mínimo e status. As
vendas baixam o estoque automaticamente e são recusadas quando não há unidades
suficientes.

O módulo Produtos da Cantina também controla entradas e saídas manuais. Cada
movimentação guarda data, motivo e, quando informado, custo de aquisição,
fornecedor, documento, lote e validade. O histórico inclui o saldo inicial,
reposições, perdas, vendas e estornos, e o painel destaca produtos sem estoque
ou abaixo do estoque mínimo.

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

## Backup e restauração

Ao iniciar, o sistema cria no máximo um backup diário em `dados/backups` e
mantém os 30 backups diários mais recentes. Para criar uma cópia manual:

```powershell
python -m src.backup_banco criar --rotulo antes_fechamento
```

Para listar e restaurar uma cópia:

```powershell
python -m src.backup_banco listar
python -m src.backup_banco restaurar NOME_DO_ARQUIVO.db
```

A restauração valida o arquivo e preserva automaticamente uma cópia do banco
atual antes de substituí-lo. O sistema deve estar fechado durante a restauração.

## Sincronização futura com Google Drive

A infraestrutura está preparada, mas permanece desativada. O banco ativo
continua local; quando o recurso for habilitado, a instalação principal poderá
publicar versões imutáveis em uma pasta do Google Drive e instalações de
consulta poderão atualizar sua cópia local. Copie
`configuracao_local.exemplo.json` para `configuracao_local.json` somente quando
for iniciar essa fase. Esse arquivo local não é enviado ao Git.

## Carteiras e manutenção

O módulo Carteiras permite criar a carteira de um residente ativo, adicionar e
corrigir créditos, consultar créditos e compras separadamente, estornar uma
compra com devolução do saldo e do estoque e ativar ou inativar a carteira.
Movimentações estornadas permanecem no histórico para auditoria.

As telas de cadastro permitem editar residentes e responsáveis, alterar o
responsável principal ou encerrar uma internação antecipadamente, editar
produtos, registrar novos preços sem apagar o histórico, ajustar estoque com
motivo, ativar ou inativar cadastros e redefinir a senha de colaboradores.

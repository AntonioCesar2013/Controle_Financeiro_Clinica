# Prompt revisado — Itens administrativos

## Notas da revisão (não fazem parte da execução)

O texto original cobre arquitetura, isolamento e testes, mas deixa ambiguidades que poderiam gerar implementações incompatíveis:

- Quantidade inicialmente positiva deve poder chegar a zero; o CHECK da tabela não pode exigir saldo sempre positivo.
- Patrimônio individual e lote com várias unidades precisam de regras diferentes.
- Um único `setor_id` não representa transferência parcial para vários destinos.
- Ajuste precisa distinguir quantidade final desejada de quantidade acrescentada/retirada.
- Histórico não deve ser opcional em um módulo com saldo, transferências e baixas.
- Valor de aquisição precisa indicar se é unitário ou total; não deve variar automaticamente com o estoque.
- Idempotência não evita que dois usuários sobrescrevam alterações diferentes; é necessário controle de versão.
- Não se deve somar quantidades de unidades incompatíveis nem confundir indicadores da página com os do filtro completo.
- A seção Administração já existe no menu, mas ainda não há um módulo backend registrado com esse nome. Setores pertencem ao Financeiro; a integração deve respeitar essa fronteira.

**Decisões propostas para esta primeira versão:** patrimônio identificado representa uma única unidade; itens sem patrimônio podem representar lotes homogêneos; transferência sempre integral; valor de aquisição é o total histórico da aquisição inicial; baixa total inativa, saída até zero não inativa; inativação manual exige saldo zero. Essas são escolhas de escopo desta revisão, não requisitos encontrados no código anterior. Transferência parcial ou custeio contínuo exigiriam outra modelagem.

---

## Prompt pronto para execução

No projeto `C:\Projetos\Controle_Financeiro_Clinica`, implemente e valide um módulo de **Itens administrativos**, independente da Cantina e dos pertences pessoais dos residentes. Siga as regras abaixo; não entregue apenas um plano.

### 1. Preparação e limites

1. Leia os `AGENTS.md` aplicáveis, confira o Git e preserve alterações preexistentes.
2. Inspecione o código atual: `src/cadastros/itens_residentes.py`, produtos/estoque da Cantina, `src/nucleo/modulos.py`, migrações versionadas, `src/infraestrutura/transacoes.py`, `operacoes.py`, validação HTTP, registro de rotas, módulos frontend e tabelas com seleção. Reutilize infraestrutura, sem copiar regras inadequadas de outros módulos.
3. Use exclusivamente bancos temporários para testes e preparação de schema. Não execute o inicializador da aplicação contra a instalação real, populadores ou `src/test.py`. Não altere `dados/clinica.db` nem bancos de produção.
4. Não faça commit, push, publicação ou upload. Não altere login, política de permissões, configuração de backup ou sincronização. Não instale dependências sem necessidade demonstrada.
5. Não gerar contas a pagar, pagamentos, lançamentos de caixa, depreciação ou conciliação a partir deste módulo. Não implementar empréstimos, reserva de itens, distribuição parcial entre setores ou custeio de entradas nesta versão.

### 2. Modelo de inventário

- Cada registro representa um bem individual ou um lote homogêneo com nome, unidade, conservação, setor e localização comuns.
- Com `codigo_patrimonio` informado: quantidade inicial exatamente 1 e saldo atual limitado a 0 ou 1. Não permitir adicionar uma segunda unidade ao mesmo patrimônio. Códigos permanecem reservados mesmo depois de baixa/inativação.
- Sem patrimônio: quantidade inicial inteira maior que zero; saldo atual inteiro maior ou igual a zero. Vários itens/lotes podem ter o mesmo nome e setor; nome não é chave única.
- Cada registro possui somente um setor/localização atual. Transferências movem todo o saldo positivo. Não oferecer quantidade parcial para transferência nem criar cópias implícitas do item.
- Quantidades são sempre inteiras. Unidades fracionárias, conversão entre unidades e estoque por vários locais estão fora do escopo.
- `valor_aquisicao` significa **valor total da aquisição inicial**, opcional, informativo e histórico. Não é preço de venda nem valor unitário. Entradas/saídas posteriores não recalculam esse campo. Não apresentar seu somatório como avaliação do estoque atual.
- `INSERVIVEL` é estado de conservação; não é sinônimo de inativo ou baixa e não deve provocar alteração de saldo automaticamente.

### 3. Schema e migrações

Criar migração numerada do módulo `administracao`, usando o executor existente. Registrar o módulo depois do Financeiro, de que depende o cadastro de setores. Não editar migrações já aplicadas nem adicionar tabelas novas ao bootstrap legado. Executar a preparação novamente não pode duplicar estruturas nem alterar dados existentes.

Criar `itens_administracao` com:

| Campo | Regra |
|---|---|
| `id` | Chave primária estável |
| `nome` | Texto obrigatório, sem espaços vazios, até 200 caracteres |
| `descricao` | Opcional, até 2000 caracteres |
| `categoria` | Opcional, até 100 caracteres |
| `codigo_patrimonio` | Opcional, até 100 caracteres; único quando informado |
| `quantidade` | Saldo atual inteiro >= 0; máximo 1 quando houver patrimônio |
| `unidade_medida` | Texto obrigatório, padrão `UN`, até 20 caracteres |
| `setor_id` | FK obrigatória para setores; exclusão restrita, sem cascata |
| `data_aquisicao` | Data opcional ISO canônica |
| `valor_aquisicao` | NULL ou centavos inteiros >= 0, dentro do limite monetário comum |
| `estado_conservacao` | `NOVO`, `BOM`, `REGULAR`, `RUIM`, `INSERVIVEL` |
| `localizacao` | Opcional, até 200 caracteres |
| `ativo` | Inteiro 0/1, padrão 1 |
| `versao` | Inteiro >= 1, para controle de concorrência |
| `cadastrado_em` | Timestamp conforme a convenção do projeto |
| `atualizado_em` | Timestamp atualizado em toda mutação confirmada |

Normalizar patrimônio com trim e maiúsculas, sem remover hífens ou outros caracteres significativos. Vazio vira NULL. Garantir unicidade dessa representação também no banco; `pat-01` e ` PAT-01 ` representam o mesmo código. Normalizar unidade com trim/maiúsculas. Preservar acentos nos textos de exibição.

Usar NOT NULL, FKs, UNIQUE e CHECKs compatíveis com SQLite, incluindo tipo inteiro quando necessário; validação somente no frontend não basta. Não criar índice comum redundante para patrimônio se o índice único já cobre a consulta. Criar índices justificados pelos filtros, sobretudo setor/situação e nome; não prometer aceleração de busca por substring apenas com índice em nome.

Criar obrigatoriamente `movimentacoes_itens_administracao`, sem exclusão em cascata:

- `id`, `item_id`, `tipo`, `data_movimentacao`, `registrado_em`;
- `quantidade_anterior`, `quantidade_movimentada` (magnitude não negativa), `variacao` (delta com sinal), `quantidade_resultante`;
- setor, nome do setor e localização anteriores/novos;
- `motivo` obrigatório até 2000 caracteres, `documento` opcional até 200;
- `versao_anterior`, `versao_resultante`;
- dados anterior/novo dos campos cadastrais/status quando o evento os alterar, usando representação consistente, por exemplo JSON;
- referência ao operador somente quando disponível no contexto atual; não inventar usuário nem exigir autenticação nova.

Tipos: `CADASTRO`, `ENTRADA`, `SAIDA`, `AJUSTE`, `TRANSFERENCIA`, `BAIXA`, `EDICAO`, `INATIVACAO`, `REATIVACAO`.

Em eventos sem alteração de saldo, delta e quantidade movimentada são zero. Para os demais, `resultante = anterior + variacao` e `quantidade_movimentada = abs(variacao)`. CADASTRO parte de zero. Indexar histórico por item/ordem de registro. Preservar snapshots para que renomear setor não reescreva a descrição de uma transferência antiga.

Não oferecer DELETE de item ou histórico. Correção ocorre por novo evento explícito, nunca por alteração silenciosa de eventos anteriores.

### 4. Operações e invariantes

Implementar domínio próprio em `src/administracao`, com funções pequenas para cadastro, edição, detalhe, listagem, movimentação, transferência, status e histórico.

| Operação | Comportamento |
|---|---|
| Cadastro | Quantidade inicial > 0, setor ativo; criar item e evento CADASTRO atomicamente |
| Edição | Alterar somente dados cadastrais, com motivo; não aceitar quantidade, setor, localização ou ativo como atalho para outra operação |
| Entrada | Somar quantidade inteira > 0; item e setor atuais ativos; respeitar limite do patrimônio individual |
| Saída | Subtrair quantidade inteira > 0, limitada ao saldo; saldo zero não inativa automaticamente |
| Ajuste | Receber `quantidade_alvo` inteira >= 0; derivar delta a partir do saldo lido na transação; motivo obrigatório; não registrar ajuste sem diferença |
| Transferência | Saldo > 0; setor de destino ativo; mover integralmente, mantendo quantidade; permitir mudança apenas de localização no mesmo setor; rejeitar destino idêntico |
| Baixa | Subtrair quantidade > 0 com motivo; baixa parcial mantém ativo; baixa que zera saldo inativa no mesmo evento/transação |
| Inativação manual | Somente saldo zero, motivo obrigatório; não diminuir ou ocultar estoque |
| Reativação | Exige setor atual ativo e motivo; mantém saldo, sem inventar entrada; item reativado com zero pode receber entrada posterior |

Regras complementares:

- Itens inativos podem ser consultados e ter dados descritivos corrigidos com histórico. Não podem sofrer movimentação/transferência antes da reativação.
- Setor inativo bloqueia cadastro, entrada, ajuste que aumente saldo e reativação. Permitir saída, baixa, ajuste redutor e transferência para setor ativo, para esvaziar o inventário antigo.
- Na transferência para setor ativo, informar também a nova localização; vazio explicitamente enviado limpa a localização, sem conservar acidentalmente a anterior.
- Unidade não pode ser alterada depois do cadastro nesta versão: não existe conversão implementada. Para o mesmo patrimônio, correção de código exige motivo, unicidade e saldo <= 1; remoção de um patrimônio existente não é permitida como atalho para transformar um bem em lote.
- Mudança de aquisição/conservação/categoria deve ficar no histórico. Não exigir unicidade de categoria nem criar novo módulo de categorias.
- Datas efetivas: texto estrito `AAAA-MM-DD`, data real, não futura. Cadastro registra data de entrada própria, padrão hoje; aquisição continua opcional. Quando aquisição existir, não admitir movimentação efetiva anterior a ela. Corrigir aquisição não pode torná-la posterior a movimentações já registradas.
- Datas retroativas representam informação documental; a mutação afeta o saldo atual. Os saldos anterior/resultante pertencem à ordem de registro, não a uma reconstrução cronológica retroativa. No histórico, ordenar por `id` crescente e mostrar data efetiva e data de registro; não apresentar uma sequência enganosa de saldos ordenada só pela data informada.
- Validar identificadores, quantidades, enums, textos, booleanos, dinheiro e datas no domínio e na adaptação HTTP. Rejeitar booleano como quantidade, frações, negativos indevidos e valores fora dos limites; não truncar silenciosamente.
- Dinheiro interno em centavos, reutilizando validadores existentes. Na API, usar a conversão reais → centavos uma única vez. Vazio/ausente no valor opcional significa NULL; zero explicitamente informado permanece zero.

### 5. Transações, concorrência e integração com setores

- Usar conexão/transação do projeto, compatível com conexão emprestada da operação HTTP e com chamada direta ao domínio. Não confirmar uma transação pertencente ao chamador.
- Leitura de saldo/versão, validação, atualização e inclusão do evento precisam ocorrer na mesma transação. Falha em qualquer etapa desfaz tudo.
- Todas as mutações de item existente exigem `versao_esperada`. Ler e validar sob lock adequado ou usar UPDATE condicional. Sucesso incrementa versão uma única vez; versão antiga retorna conflito e não grava evento. Não tentar reaplicar automaticamente uma edição contra uma versão nova.
- Idempotência continua sendo responsabilidade do pipeline existente: mesma chave e payload retornam o resultado original, mesmo que a versão do item tenha mudado depois. Mesma chave e outro payload devem ser recusados. Não criar armazenamento paralelo de chaves.
- Setores pertencem ao Financeiro. Expor ou reutilizar contrato mínimo em `src/financeiro/api_publica.py` para consultar/validar setor, participando da conexão corrente quando necessário. Não duplicar setores nem mover suas tabelas. A FK entre módulos é permitida; manter a leitura das tabelas internas de setores encapsulada no módulo dono.
- Verificar existência/atividade do setor na gravação, mesmo quando a tela já filtrou opções. Preservar consultas de setores inativos e integridade referencial.

### 6. API

Usar estas rotas, integradas ao registro, validação e envelope de respostas atual:

- `GET /api/administracao/itens`
- `GET /api/administracao/itens/detalhe?id=...`
- `GET /api/administracao/itens/historico?id=...&pagina=...&tamanho=...`
- `POST /api/administracao/itens`
- `POST /api/administracao/itens/editar`
- `POST /api/administracao/itens/movimentar`
- `POST /api/administracao/itens/transferir`
- `POST /api/administracao/itens/status`

Cadastro recebe os campos cadastrais, `quantidade_inicial`, `data_movimentacao` e motivo/documento inicial; não aceitar saldo atual ou versão definidos pelo cliente. Retornar ID e versão.

Movimentação recebe `id`, `versao_esperada`, `tipo`, data, motivo, documento e **ou** `quantidade` para entrada/saída/baixa **ou** `quantidade_alvo` para ajuste. Recusar combinações ambíguas e tipos de evento que só podem ser gerados internamente.

Transferência recebe ID, versão, `setor_destino_id`, `localizacao_destino`, data e motivo. Status recebe ID, versão, `ativo` e motivo; não movimenta quantidade. Edição recebe campos permitidos e motivo, sem aceitar mutações operacionais ocultas.

Listagem aceita `busca`, `setor_id`, `categoria`, `estado_conservacao`, `ativo`, `pagina`, `tamanho` e `ordem`. Definir e documentar ausência de `ativo` como todos, sem confundir `ativo=0` com ausência. Padrão 50 registros, limite 200. Filtros antes de paginação; ordenação por whitelist e ID como desempate. SQL parametrizado. Busca sem distinguir acentos/caixa, conforme padrão existente.

Retornar linhas, página/tamanho, total geral, total filtrado e indicadores calculados sobre o conjunto filtrado inteiro, não apenas a página. Histórico paginado deve permitir acessar todos os eventos. Erros devem identificar validação, registro inexistente, patrimônio duplicado, saldo insuficiente e conflito de versão/idempotência, usando o mecanismo HTTP existente sem expor traceback/SQL.

### 7. Interface e layout

- Reutilizar o menu **Administração** já existente e acrescentar **Itens administrativos**. Não substituir Colaboradores, Configurações ou Sair.
- Registrar painel no mecanismo de módulos frontend. Extrair comportamento para componente próprio, por exemplo `frontend/js/components/itens-administracao.js`; manter `app.js` como integração mínima. Não adicionar framework.
- Usar estilos e componentes atuais: cabeçalho, resumo, filtros, tabela responsiva, seleção única e barra de ações acima da tabela. Sem coluna Ações ou botões por linha.
- Barra “acima da tabela” não significa posicionamento fixo sobre a janela. Seguir o padrão atual, sem cobrir cabeçalhos/conteúdo. Suportar teclado, rótulos, foco visível, mensagens acessíveis e tela estreita.
- Colunas: nome, patrimônio, categoria, setor, localização, quantidade, unidade, conservação e situação.
- Indicadores do filtro completo: registros cadastrados, ativos, registros RUIM e INSERVIVEL. Quantidade em inventário deve ser agrupada por unidade (`20 UN`, `3 CX`), sem total único de unidades incompatíveis. Identificar claramente o escopo filtrado.
- Novo item permanece disponível; sem setor ativo, explicar e direcionar ao cadastro existente. Editar/Histórico habilitam com seleção. Movimentar/Transferir/Status respeitam as regras e o estado selecionado. Mostrar por que uma ação está indisponível quando necessário.
- Novo item: todos os campos cadastrais, quantidade inicial, data de entrada, motivo inicial (padrão claro “Cadastro inicial”) e documento opcional. Exibir “Valor total da aquisição inicial (opcional)”.
- Edição: preencher valores atuais; quantidade/setor/localização/unidade/status não editáveis nesse formulário. Exigir motivo das alterações.
- Movimentação: tipo, quantidade ou saldo final contado (para AJUSTE), data, motivo e documento. Mostrar saldo atual e prévia do saldo resultante usando inteiros. BAIXA total informa explicitamente que inativará o item.
- Transferência: mostrar setor/localização atuais, pré-selecionar conscientemente o destino sem trocar dados ao simples abrir/salvar, informar que move todo o saldo, exigir data/motivo.
- Histórico: apresentar tipo, data efetiva, registro, quantidades e delta, setor/localização anteriores/novos, motivo/documento e alterações cadastrais/status. Manter eventos de itens baixados/inativos acessíveis.
- Escapar textos em HTML e atributos. Ao concluir, atualizar detalhe/tabela/indicadores preservando filtros/página quando válida. Limpar seleção se o item sair do filtro. Em conflito, manter os dados digitados para comparação e orientar recarregar, sem sobrescrever automaticamente.
- Usar o cliente API existente para estados de envio/reenvio e desabilitar submissão duplicada durante o processamento.

### 8. Testes e critérios de aceite

Criar testes backend/API em bancos temporários e frontend de comportamento, não apenas busca de strings no código. Cobrir:

1. Migração em banco novo e banco temporário com dados dos outros módulos; reexecução preserva dados, schema e histórico. Falha reverte a migração. Registrar módulo sem criar painel duplicado.
2. Patrimônio normalizado único inclusive em itens inativos; vários NULL; nomes repetidos permitidos; patrimônio com quantidade > 1 recusado.
3. Obrigatoriedade, comprimentos, tipos, datas impossíveis/futuras, limites monetários, NULL versus zero e dinheiro convertido uma vez.
4. Eventos iniciais e operações da tabela de regras; saldo nunca negativo; ajuste para zero; baixa parcial/total; saída que zera sem inativar; inativação com saldo recusada; reativação sem alteração de saldo.
5. Setor inexistente/inativo; bloqueio de aumento e permissão de esvaziamento/transferência; renomear setor não altera snapshots históricos.
6. Transferência integral preserva quantidade, registra origem/destino e rejeita destino idêntico; edição não pode contornar regras operacionais.
7. Falha ao inserir histórico reverte a mutação. Duas saídas concorrentes não excedem saldo; duas alterações com a mesma versão não sobrescrevem uma à outra.
8. Reenvio com mesma chave não duplica cadastro/evento; mesma chave com outro payload conflita; resposta perdida recuperada preserva resultado original; versão obsoleta com chave nova não grava nada.
9. Busca/filtros, inclusive inativos, paginação, ordenação inválida, desempate e indicadores do filtro completo. Quantidades de UN e CX nunca são somadas em um único indicador.
10. Menu preservado, seleção por teclado/mouse, ausência da coluna Ações, botões conforme elegibilidade, formulários preenchidos, zero/saldo alvo, erro de conflito e escape de HTML no histórico e nas tabelas.
11. Nenhuma aquisição/movimentação administrativa cria conta, pagamento, movimentação de caixa, estoque da Cantina ou pertence pessoal.

Executar novos testes e, quando presentes, as suítes existentes:

```text
python -m unittest discover -s tests -p 'test_fluxos*.py'
python -m unittest discover -s tests -p test_regressoes.py
python -m unittest discover -s tests -p test_operacoes_api.py
python -m unittest discover -s tests -p test_arquitetura_modular.py
python -m unittest discover -s tests -p test_itens_residentes.py
node tests/api.mjs
node tests/interface_visual.mjs
node tests/modulos_frontend.mjs
node tests/itens_residentes.mjs
node --check frontend/js/app.js
```

Executar também os testes existentes de cadastros e os testes pertinentes aos arquivos compartilhados alterados. Verificar sintaxe dos novos arquivos JS. Se usar teste visual/navegador, iniciar instância isolada conectada somente a banco temporário; não usar a instância real. Reportar claramente verificações visuais não realizadas e dependências indisponíveis, sem afirmar aprovação.

### 9. Entrega

Revisar o diff e documentar: tabelas/migrações, contrato das operações/API, regras e decisões de escopo, como usar o menu e formulários, arquivos alterados, testes e resultados, limitações e necessidade de reiniciar.

Informar que a migração foi validada somente em bancos temporários e será aplicada pela inicialização normal quando a versão for utilizada. Não iniciar nem migrar a instalação real nesta tarefa. Não modificar dados preexistentes automaticamente e não implementar operações financeiras fora do escopo.

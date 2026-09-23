# Auditoria final para produção — 21/09/2026

## Parecer

**Não recomendo a entrada em produção antes de resolver os pontos de backup abaixo.** A suíte automatizada passou, mas há um bloqueio funcional para configurar a proteção dos dados no modo atual, sem login. Recomendo também corrigir os três problemas do inventário antes de disponibilizar o novo módulo.

O uso por um único administrador, sem login, foi considerado requisito. A ausência de login não foi classificada como defeito nem se recomenda implantar autenticação nesta entrega.

## Verificações concluídas

- 139 testes Python aprovados no ambiente `.venv` utilizado pelo projeto, em 63,155 segundos. Registro: `tmp/auditoria_final_python_producao.log`.
- 14 scripts de testes JavaScript aprovados: API, backup, cadastros, conferência, contas a pagar, contas a receber, gráficos, datas, documentos, interface visual, itens administrativos, itens de residentes, módulos e fluxos.
- Verificação de sintaxe de todos os arquivos JavaScript do frontend aprovada.
- Dependências de execução e dos provedores de backup importadas com sucesso no ambiente do projeto.
- Banco real aberto somente para leitura e copiado para um banco temporário. Integridade SQLite aprovada e nenhuma violação de chave estrangeira antes ou depois das migrações.
- Migrações executadas duas vezes na cópia, sem alteração da contagem de registros das tabelas existentes, exceto a tabela de controle de migrações. Isso verifica preservação de contagens, não equivalência integral de todos os campos.
- Na cópia, nenhuma ocorrência nas consultas para saldo negativo de cobranças e contas a pagar, divergência de status de cobranças, conta cancelada com pagamento ou estoque negativo.
- Migrações pendentes identificadas: `cadastros:4` e `administracao:1`. Foram aplicadas apenas na cópia temporária.

O primeiro teste com o Python auxiliar encontrou duas dependências ausentes nesse runtime. A execução posterior no ambiente real do projeto passou integralmente; não se trata de falha da aplicação.

## Achados confirmados

### 1. P1 — Backup automático desativado e sem destino

**Evidência:** a configuração carregada para o usuário Windows atual retornou `backup_enabled=false`, pasta vazia, Drive e R2 desativados e arquivo de configuração inexistente. O backup local mais recente encontrado em `dados/backups` tem data de 12/09/2026, nove dias antes desta auditoria. Não foi verificada a existência de cópias externas feitas fora do sistema.

**Impacto:** iniciar a operação nessa condição deixa os novos lançamentos sem cópia automática configurada. A suíte de testes de backup não substitui uma cópia operacional recuperável.

**Ação:** definir um destino acessível, preferencialmente em outro dispositivo ou com cópia externa; configurar o agendamento; gerar uma cópia atual e restaurá-la em ambiente separado. Conferir integridade, abertura e dados representativos nessa restauração. Não restaurar sobre o banco real para fazer o teste.

### 2. P1 — Painel de backup exige sessão no modo sem login

**Local:** `src/interface/rotas/backup.py`, função `dispatch`; `frontend/js/app.js`, inicialização e tratamento de não autorizado.

**Reprodução:** chamar `dispatch` para `/api/backup/status` com `_sessao()` retornando `None` produz HTTP 401 e “Sessão não autenticada.”. A inicialização da interface pula `checkAccess()` e abre diretamente o menu; o cliente trata o 401 exibindo login.

**Impacto:** o fluxo normal escolhido para produção não permite consultar/configurar o novo backup sem cair numa exigência de autenticação.

**Correção:** tornar o módulo de backup compatível com o modo local de administrador único, explicitamente definido pelo projeto. Preservar a vinculação local do servidor, as verificações de origem e o tratamento seguro de credenciais. Não adicionar tela de login nem simplesmente remover indiscriminadamente as proteções. Ajustar os testes de integração para refletir o modo efetivo de operação.

### 3. P2 — Transferência escolhe destino implicitamente quando a origem está inativa

**Local:** `frontend/js/components/itens-administracao.js`, `open`, ramo `transfer`.

**Reprodução:** item no setor 9 inativo, com setor 2 ativo disponível. O formulário produz somente `<option value="2">...` no seletor de destino; o setor atual não está na lista e não existe opção vazia. O navegador seleciona o primeiro setor ativo.

**Impacto:** o administrador pode salvar uma transferência para um setor que não escolheu conscientemente.

**Correção:** exigir escolha explícita do destino quando a origem não for uma opção válida. Usar opção inicial vazia e validação obrigatória; mostrar origem e destino antes da confirmação. Sem setores ativos, explicar a indisponibilidade e impedir envio.

### 4. P2 — Movimentação não apresenta saldo previsto nem alerta sobre baixa total

**Local:** `frontend/js/components/itens-administracao.js`, ramos `move` e `change`; `src/administracao/itens.py`, `movimentar`.

**Evidência:** o formulário apresenta somente saldo atual e o rótulo compartilhado “Quantidade / saldo final no ajuste”. Os atributos de tipo e quantidade existem, mas a função `change` trata apenas filtros. A baixa total inativa o item no domínio, sem aviso correspondente no formulário.

**Impacto:** o usuário pode interpretar ajuste como quantidade a acrescentar ou executar uma baixa sem perceber a inativação automática. As validações do servidor evitam saldo negativo, mas não evitam erro de intenção.

**Correção:** diferenciar visualmente quantidade movimentada de saldo final desejado; mostrar saldo previsto ao alterar tipo/quantidade; informar claramente a inativação na baixa total antes do envio. Manter as regras atuais no servidor.

### 5. P2 — API rejeita valor de aquisição numérico válido

**Local:** `src/interface/validacao.py`, conjunto `MONETARIOS`.

**Reprodução:** com os demais campos válidos, `valor_aquisicao: 10.5` é rejeitado como campo que deveria conter texto, enquanto `valor_aquisicao: "10.50"` é aceito. O campo não consta na classificação de monetários.

**Impacto:** inconsistência no contrato da API e rejeição de clientes que enviem números JSON. O formulário atual envia texto, portanto esse caso não bloqueia seu cadastro normal.

**Correção:** classificar e validar o campo conforme o padrão monetário existente, sem conversão duplicada para centavos. Cobrir número, texto decimal, zero, ausência, negativo e valores inválidos.

## Limites e liberação

Esta revisão combina inspeção de código, testes automatizados, reproduções pontuais e verificações agregadas numa cópia dos dados. Não houve homologação visual completa na janela WebView, teste real de upload para Drive/R2 ou simulação de falha física do computador. Os testes com serviços externos usam substitutos controlados. Aprovação nos testes não comprova ausência de todos os defeitos.

Antes da liberação:

1. Corrigir o acesso ao backup no modo sem login.
2. Configurar e executar backup atual; comprovar recuperação em banco separado.
3. Corrigir e verificar os três achados do inventário.
4. Fazer uma passagem manual, com dados de teste em ambiente separado, por cadastro/internação, pagamento e estorno, recebimento e estorno, venda da cantina e estorno, inventário, recibos e conferência.
5. Aplicar as migrações na implantação somente com cópia recuperável anterior. Conferir integridade e abertura após atualizar.

Nenhum código de produção ou dado operacional foi alterado nesta auditoria. Foram acrescentados apenas este relatório e o utilitário de inspeção `docs/verificar_pre_producao_2026_09_21.py`; registros de execução ficaram em `tmp`.

## Prompt para executar as correções

No projeto `C:\Projetos\Controle_Financeiro_Clinica`, corrija os achados 2 a 5 de `docs/AUDITORIA_FINAL_PRODUCAO_2026-09-21.md`. O sistema será usado localmente por um único administrador e continuará sem login. Não implemente autenticação, usuários ou perfis nesta tarefa.

Leia as instruções do repositório, preserve as alterações existentes e examine os padrões atuais antes de modificar arquivos. Adapte o backup ao modo local sem login, preservando as proteções aplicáveis de origem, acesso local e credenciais. Corrija a seleção implícita de setor na transferência, acrescente previsão de saldo e aviso de inativação à baixa total e ajuste a validação de `valor_aquisicao` sem duplicar conversões monetárias.

Adicione testes de regressão que reproduzam cada problema. Para backup, exercite a integração da rota no modo efetivo sem sessão e mantenha cobertura das proteções pertinentes. Para transferência, cubra origem inativa, escolha explícita e ausência de destino ativo. Para movimentação, cubra entrada, saída, ajuste e baixa total, com prévia coerente com o servidor. Para aquisição, cubra número JSON, texto decimal, zero, ausência e valores inválidos.

Execute as suítes Python e JavaScript e as verificações de sintaxe. Use bancos temporários; não altere o banco real, não execute restauração sobre ele e não habilite destino externo inventado. Identifique a configuração necessária para resolver o achado 1; depois de informado o destino, configure o backup autorizado e valide sua recuperação em ambiente separado. Diferencie correções concluídas de pendências operacionais e informe arquivos alterados, resultados dos testes e riscos remanescentes. Não declare produção liberada enquanto o backup recuperável e a homologação final estiverem pendentes.

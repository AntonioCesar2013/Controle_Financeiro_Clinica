# Relatório de estado do projeto — Controle Financeiro Clínica

Atualizado em: 31/08/2026  
Objetivo: permitir que outra IA ou outro desenvolvedor compreenda rapidamente a arquitetura, o que já funciona, o estado dos dados, os riscos conhecidos e a ordem recomendada para continuar o desenvolvimento.

## 1. Instruções importantes para a próxima IA

1. Leia este relatório e o `README.md` antes de alterar o projeto.
2. Preserve todas as alterações locais. O repositório está com vários arquivos modificados que ainda não foram incluídos em um novo commit.
3. Não apague, recrie, substitua nem versione o banco real `dados/clinica.db`. Os arquivos de banco estão ignorados pelo Git.
4. Não execute a descoberta completa de testes diretamente sobre o projeto/banco real. Há scripts antigos com nome `test_*.py` que são descobertos como testes e podem executar rotinas inadequadas. Para uma varredura completa, copie o projeto para uma pasta temporária e use um banco isolado.
5. Prefira executar os testes seguros nominalmente, especialmente `src.test_manutencao_operacional` e `src.test_integracao_frontend`.
6. O login está propositalmente desativado durante a fase de testes. Não o torne obrigatório sem solicitação explícita do usuário.
7. Não faça commit nem push sem solicitação explícita. Quando solicitado, existe o script `commit.ps1`, mas revise o que será incluído antes de executá-lo, pois ele usa `git add .`.
8. Preserve as despesas e entradas bancárias reais já importadas. Dados fictícios não devem voltar ao banco.

## 2. Resumo executivo

O sistema está no estágio de **MVP funcional para testes locais ou piloto controlado**. A base principal já existe: cadastros, internações, financeiro, carteiras, Cantina com leitor de código de barras, estoque e relatórios A4.

Os fluxos mais recentes funcionam nos testes direcionados e as telas principais carregam corretamente. Entretanto, o sistema ainda não deve ser considerado pronto para produção ou para uso simultâneo por vários usuários. Antes disso, é necessário concluir itens de integridade transacional, segurança, conciliação financeira, limpeza da suíte de testes e rotinas de backup.

Estado resumido:

- Arquitetura principal: implementada.
- Interface integrada ao backend: implementada.
- Cadastros essenciais: implementados.
- Financeiro básico: implementado.
- Carteiras e Cantina: implementadas.
- Estoque básico: implementado.
- Relatórios A4: implementados, mas ainda incompletos.
- Testes direcionados atuais: aprovados.
- Suíte completa: ainda apresenta testes antigos/quebrados.
- Autenticação: implementada, mas temporariamente desativada.
- Prontidão para produção: ainda não atingida.
- Alterações atuais no Git: ainda não consolidadas em commit/push.

## 3. Arquitetura atual

### Frontend

- HTML, CSS e JavaScript puro, sem framework.
- Aplicação de página única localizada em `frontend/`.
- Menu flutuante e fixo à esquerda.
- Os módulos ocupam o restante da tela, com margens reduzidas.
- Interface responsiva validada em resolução de computador e celular, sem rolagem horizontal indevida.
- Comunicação com o backend por rotas HTTP/JSON.

Ordem atual do menu:

1. Dashboard
2. Relatórios
3. Financeiro
4. Carteiras
5. Cantina
6. Internações
7. Residentes
8. Responsáveis
9. Colaboradores
10. Itens
11. Configurações
12. Sair

O módulo Financeiro possui as áreas de visão financeira, contas a receber, contas a pagar, fluxo de caixa e despesas.

### Backend

- Python, usando principalmente a biblioteca padrão.
- Servidor HTTP em `src/servidor.py`.
- Banco SQLite em `dados/clinica.db`.
- Criação e migração do esquema centralizadas em `src/banco.py`.
- Inicialização disponível por `main.py`, `iniciar.cmd` e `iniciar.ps1`.
- Na primeira execução, o sistema prepara a estrutura necessária automaticamente.

### Banco de dados

Principais tabelas existentes:

- `residentes`
- `responsaveis`
- `colaboradores`
- `residente_responsavel`
- `internacoes`
- `cobrancas`
- `recebimentos`
- `entradas_bancarias`
- `setores`
- `tipos_despesa`
- `despesas`
- `contas_pagar`
- `pagamentos_saida`
- `configuracoes_financeiras`
- `itens`
- `itens_valores`
- `carteiras`
- `vendas_cantina`
- `vendas_cantina_itens`
- `movimentacoes_carteira`
- `movimentacoes_estoque`

## 4. Funcionalidades implementadas

### Colaboradores e autenticação

- Cadastro de colaborador com nome, CPF, senha e status.
- Senhas armazenadas com hash PBKDF2-SHA256 e 600.000 iterações.
- Fluxos de primeiro acesso, login e sessão disponíveis.
- O login obrigatório está comentado temporariamente para facilitar os testes.

Pontos onde a exigência de autenticação foi desativada:

- `frontend/js/app.js`: chamada de verificação de acesso no início da aplicação.
- `frontend/js/app.js`: retorno à tela de login ao sair.
- `src/servidor.py`: proteções das rotas GET e POST.

### Residentes, responsáveis e internações

- Cadastro de residentes.
- Cadastro de responsáveis e associação com residentes.
- Cadastro de internação com responsável principal.
- Alteração do responsável principal.
- Encerramento antecipado da internação.
- Geração da cobrança de entrada e das mensalidades previstas.
- Regra automática de status: todo residente começa inativo e só permanece ativo enquanto houver internação dentro do período válido.

### Financeiro

- Cadastro de setores, tipos de despesa e despesas.
- Contas a pagar ligadas às despesas.
- Pagamentos parciais ou integrais.
- Cancelamento, exclusão/estorno de pagamentos de saída.
- Contas a receber geradas pelas internações.
- Recebimentos parciais ou integrais.
- Descontos e estorno/exclusão de recebimentos.
- Quando a forma de pagamento ou recebimento está ausente, o sistema assume PIX.
- Fluxo de caixa reunindo recebimentos, entradas bancárias e pagamentos de saída.
- Despesas reais importadas dos relatórios fornecidos pelo usuário.
- Entradas bancárias reais importadas do relatório bancário.

### Carteiras dos residentes

- Criação de carteira para residente ativo.
- Saldo inicial e créditos posteriores.
- Correção/estorno de crédito.
- Ativação e inativação da carteira.
- Consulta do saldo do residente selecionado.
- Histórico das movimentações e compras.

### Cantina

A Cantina funciona como um pequeno mercado interno para os residentes:

- Leitura de código de barras por leitor USB/HID, usando o campo de leitura e a tecla Enter.
- Inclusão manual de produto.
- Carrinho de compra.
- Leituras repetidas aumentam a quantidade do item.
- Uma venda pode conter vários produtos em um único cupom.
- A conclusão da venda desconta, na mesma operação, o saldo da carteira e o estoque.
- Validação de residente, carteira, produto, preço, estoque e saldo.
- Estorno integral do cupom, devolvendo o valor à carteira e os itens ao estoque.
- Histórico por cupom, itens vendidos e movimentações relacionadas.

### Produtos e estoque

- Nome, código de barras, descrição, categoria e unidade.
- Preço de venda com histórico de valores.
- Estoque atual e estoque mínimo.
- Status ativo/inativo.
- Entrada e saída manual de estoque com motivo obrigatório.
- Campos opcionais para custo, fornecedor, documento, lote e validade.
- Histórico de saldo inicial, ajustes manuais, vendas e estornos.
- Indicadores de estoque baixo e produto sem estoque.

### Relatórios

Existem visualização no sistema e impressão em papel A4 para:

- Financeiro.
- Despesas por setor.
- Internações.
- Residentes.
- Cantina.
- Carteiras.
- Estoque.
- Colaboradores.

## 5. Estado atual do banco real

Última auditoria de leitura realizada no banco `dados/clinica.db`:

| Verificação | Resultado |
|---|---:|
| Integridade do SQLite | OK |
| Violações de chave estrangeira existentes | 0 |
| Colaboradores | 1 |
| Residentes | 1 |
| Internações | 0 |
| Cobranças | 0 |
| Recebimentos | 0 |
| Entradas bancárias | 64 |
| Despesas | 8 |
| Contas a pagar | 8 |
| Pagamentos de saída | 8 |
| Produtos | 0 |
| Carteiras | 0 |
| Vendas da Cantina | 0 |
| Contas pagas acima do devido | 0 |
| Cobranças recebidas acima do devido | 0 |
| Contratos financeiros divergentes | 0 |
| Saldos de carteira divergentes | 0 |

Observação: as 64 entradas bancárias estão importadas como movimentos brutos. Ainda falta uma rotina de conciliação para relacioná-las a residentes, cobranças ou outras origens.

## 6. Estado dos testes e validações

### Resultado confiável

- 50 testes atuais e autocontidos passaram em uma cópia isolada do projeto.
- Os testes direcionados dos fluxos mais recentes, especialmente manutenção operacional e integração do frontend, também passaram.
- As telas principais foram abertas e verificadas visualmente.
- Em 1280 × 720, o menu ficou fixo à esquerda e o conteúdo utilizou corretamente o espaço restante.
- Em 390 × 844, não houve rolagem horizontal e o conteúdo permaneceu utilizável.

### Problemas da descoberta completa

A descoberta completa executa 65 casos e atualmente termina com 6 falhas e 4 erros. Isso não representa, isoladamente, uma quebra dos fluxos novos: a maior parte vem de arquivos antigos ou scripts manuais tratados incorretamente como testes.

Arquivos/problemáticas conhecidas:

- `src/test.py`, `src/test_contas_pagar.py` e `src/test_pagamentos.py`: são scripts manuais com nome de teste e podem encerrar o processo com `SystemExit`.
- `src/test_popular_despesas_reais.py`: pressupõe que já exista um colaborador e pode deixar conexão aberta quando uma asserção falha.
- `src/test_cantina.py`: conserva expectativas antigas sobre o status inicial dos produtos.
- `src/test_itens.py`: espera que um item novo já seja ativo, mas o esquema atual o cria inativo por padrão.

A suíte precisa ser reorganizada para separar testes automatizados, scripts manuais e testes que dependem de dados prévios.

## 7. Pendências prioritárias

### Prioridade crítica — antes de produção

1. **Reativar a autenticação**, depois que a fase de testes livres terminar.
2. **Ativar `PRAGMA foreign_keys = ON` em todas as conexões SQLite.** Atualmente a função geral de conexão não garante essa proteção. O banco auditado não possui órfãos, mas futuras gravações podem gerar inconsistências.
3. **Limpar e estabilizar a suíte de testes**, separando scripts manuais e corrigindo as expectativas antigas.
4. **Tornar atômicos o cadastro da internação e a geração das cobranças.** Hoje a internação é confirmada antes da geração das cobranças; se a segunda etapa falhar, pode existir internação sem o financeiro correspondente.
5. **Consolidar e versionar as alterações atuais** quando o usuário solicitar commit e push. A versão mais recente do sistema ainda está somente na árvore de trabalho local.
6. **Criar rotina confiável de backup e restauração** para uso diário, não apenas em populadores ou migrações manuais.

### Prioridade alta — regras de negócio

1. Impedir internações duplicadas ou com períodos sobrepostos para o mesmo residente.
2. Validar se o responsável escolhido para uma nova internação está ativo.
3. Representar internação futura como `AGENDADA`; atualmente ela pode aparecer como encerrada até chegar a data inicial.
4. Permitir correção de contrato, datas, período e valores da internação, com regeneração segura das cobranças.
5. Criar tela e processo de conciliação das entradas bancárias com cobranças e residentes.
6. Tornar editáveis e efetivamente aplicáveis as configurações financeiras de juros e multa, ou removê-las da interface enquanto não forem usadas.
7. Implementar geração real das parcelas futuras para despesas recorrentes. Hoje o sistema apenas armazena o indicador de recorrência.
8. Validar a data de recebimento e corrigir a mensagem de saldo restante, que em um ponto apresenta centavos como se fossem reais.
9. Reforçar transações financeiras para cenários simultâneos, pois o servidor aceita requisições concorrentes.

### Prioridade operacional

1. Registrar qual colaborador realizou cada inclusão, alteração, pagamento ou estorno.
2. Ligar a entrada de estoque por compra à despesa/conta a pagar correspondente.
3. Implementar estoque real por lote, controle de saldo por lote, FIFO/FEFO e alertas de validade. Os campos de lote e validade existem no movimento, mas ainda não formam um controle por lote.
4. Criar relatórios detalhados de contas a receber, contas a pagar, conciliação bancária, movimentações de estoque, produtos a vencer e cupons.
5. Corrigir o resumo do relatório da Cantina para contar cupons distintos, e não linhas de itens vendidos.
6. Garantir que o relatório de estoque nunca selecione preço com início de vigência no futuro.
7. Criar impressão de cupom/comprovante da venda da Cantina.
8. Validar os dígitos verificadores do CPF, além de apenas conferir se há 11 números.
9. Adicionar expiração de sessão e invalidar sessões quando a senha ou o status do colaborador mudar.
10. Revisar `requirements.txt`, pois `python-dateutil` aparentemente não é mais necessário.
11. Corrigir a numeração e atualizar pequenos trechos do `README.md`.

## 8. Alterações locais ainda não consolidadas

Na última verificação, os seguintes arquivos estavam modificados ou ainda não rastreados:

```text
M  README.md
M  frontend/css/style.css
M  frontend/js/app.js
M  src/banco.py
M  src/cantina.py
M  src/cobrancas.py
M  src/colaboradores.py
M  src/consultas_interface.py
M  src/despesas.py
M  src/internacoes.py
M  src/itens.py
M  src/popular_despesas_reais.py
M  src/relatorios.py
M  src/residentes.py
M  src/responsaveis.py
M  src/servidor.py
M  src/test_integracao_frontend.py
?? src/test_manutencao_operacional.py
?? RELATORIO_ESTADO_PROJETO.md
```

Últimos commits conhecidos:

- `eca207e` — Implementa cantina, dados reais, cadastros e relatórios.
- `8bc67cb` — Integra frontend ao backend com autenticação.
- `6144ad1` — Padroniza nomenclatura das tabelas de itens.

Antes de um próximo commit, executar pelo menos:

1. Revisão do estado e das diferenças do Git.
2. Testes direcionados em banco isolado.
3. Verificação para garantir que nenhum arquivo `.db`, cópia de banco, PDF confidencial ou arquivo temporário será incluído.
4. Revisão do conteúdo selecionado pelo `commit.ps1` antes de confirmar o envio.

## 9. Sequência recomendada de continuidade

### Etapa 1 — estabilização

- Corrigir e organizar os testes.
- Ativar chaves estrangeiras em todas as conexões.
- Unificar internação e geração de cobranças em uma única transação.
- Adicionar validações de datas, sobreposição e concorrência.

### Etapa 2 — segurança e operação real

- Reativar login.
- Implementar expiração/invalidação de sessões.
- Criar auditoria por colaborador.
- Criar backup e restauração testados.

### Etapa 3 — fechamento financeiro

- Implementar conciliação bancária.
- Aplicar juros e multas configuráveis.
- Gerar contas recorrentes.
- Criar fluxos seguros de correção dos lançamentos e contratos.

### Etapa 4 — estoque e relatórios

- Controlar estoque por lote e validade.
- Integrar compra de estoque com contas a pagar.
- Completar os relatórios operacionais e financeiros.
- Criar cupom da Cantina.

### Etapa 5 — preparação da versão utilizável

- Executar toda a suíte sem falhas em ambiente isolado.
- Fazer teste completo, da primeira execução até os principais fluxos.
- Validar em outra máquina limpa.
- Revisar documentação.
- Fazer commit e push somente após autorização do usuário.

## 10. Critério sugerido para considerar o sistema funcional em produção

O sistema poderá avançar de MVP para uma primeira versão operacional quando, no mínimo:

- a suíte automatizada estiver limpa e reproduzível;
- autenticação e auditoria estiverem ativas;
- chaves estrangeiras e operações financeiras forem transacionalmente seguras;
- houver backup e restauração testados;
- internações não puderem gerar contratos sobrepostos ou financeiro incompleto;
- entradas bancárias puderem ser conciliadas;
- um teste de primeira instalação em outra máquina for concluído com sucesso;
- o código correspondente estiver commitado e enviado ao repositório remoto.

Até lá, a classificação recomendada é: **MVP funcional, adequado para desenvolvimento e testes controlados, ainda não pronto para produção**.

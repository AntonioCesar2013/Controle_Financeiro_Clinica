# Arquitetura do monólito modular

O Controle Financeiro da Clínica é uma única aplicação Python, com um único
banco SQLite e uma interface HTML/CSS/JavaScript executada no WebView2. A
modularização organiza responsabilidades; ela não cria serviços, processos ou
bancos separados.

## Núcleo

`src/nucleo` mantém o registro dos módulos, o executor de migrações e o ponto de
extensão de permissões. `src/infraestrutura` fornece conexão SQLite, backup,
auditoria e configuração da instalação. Cadastros compartilhados de residentes,
responsáveis, colaboradores e internações ficam em `src/cadastros`.

O registro é explícito e ordenado: Cadastros, Financeiro e Cantina. Cada
descritor `modulo.py` expõe nome, preparação do banco e permissões futuras.

## Módulos de negócio

- Financeiro possui contratos monetários, cobranças, recebimentos, despesas,
  contas, pagamentos, caixa, estornos, recibos e relatórios financeiros.
- Cantina possui produtos, preços, estoque, carteiras, créditos, vendas e
  estornos. Saldo negativo é permitido intencionalmente.

Um módulo não deve executar SQL nas tabelas internas de outro. A comunicação
usa `api_publica.py`. A API pública do Financeiro recebe opcionalmente uma
conexão existente, permitindo que cadastro da internação e geração/ajuste do
contrato sejam atômicos. Ela retorna o resultado financeiro existente e pode
propagar `ValueError` para violações de regra.

## Banco e migrações

`src.infraestrutura.banco.criar_tabelas()` coordena a preparação. O bootstrap
idempotente legado permanece para reconhecer todas as versões históricas do
banco, inclusive a conversão monetária com backup. Depois dele, cada módulo
executa migrações numeradas. `migracoes_schema` registra `(modulo, versao)`;
cada versão roda uma vez, com savepoint, e todos os módulos participam da mesma
transação. Novas alterações de schema devem ser adicionadas ao `modulo.py` do
dono, nunca ao bootstrap legado.

## HTTP e frontend

`src/interface/servidor.py` mantém transporte, JSON, arquivos estáticos,
restrição a `127.0.0.1` e auditoria. As rotas GET são registradas em
`src/interface/rotas` por área. URLs e formatos existentes foram preservados.

No cliente, `frontend/js/core` contém API, estado, roteamento e o ponto de
extensão de permissões. `frontend/js/modules` registra os painéis de Cadastros,
Financeiro e Cantina. `index.html` continua sendo a base visual e os painéis
continuam montados em JavaScript. Por isso, os antigos HTML vazios foram
removidos em vez de mantidos como placeholders.

## Controle de acesso futuro

Os descritores backend declaram permissões como `financeiro.receber` e
`cantina.vender`; `src/nucleo/permissoes.py` e
`frontend/js/core/permissions.js` são os pontos de integração. Ambos permanecem
permissivos nesta etapa. A autenticação e o fluxo de testes não foram alterados.

## Como adicionar um módulo futuro

1. Criar `src/<nome>/modulo.py` com um `Modulo` e migrações numeradas.
2. Registrar seu caminho em `_CAMINHOS`, em `src/nucleo/modulos.py`.
3. Expor integrações estritamente necessárias em `api_publica.py`.
4. Criar seu arquivo de rotas e adicioná-lo ao registro de rotas.
5. Criar `frontend/js/modules/<nome>/index.js` e registrá-lo no agregador.
6. Adicionar testes de migração, rollback, rotas e carregamento do frontend.

Esse padrão permite adicionar Cozinha no futuro sem implementá-la agora.

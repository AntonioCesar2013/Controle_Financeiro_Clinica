# Auditoria de contas a pagar — 16/09/2026

Escopo: contas, despesas/setores usados nos lançamentos, pagamentos, descontos, cancelamentos, recorrências, filtros e totais. Foram revisados domínio, rotas e frontend. Todos os dados de reprodução foram criados em bancos temporários. Nenhuma correção funcional foi aplicada. As alterações de cadastros já presentes no diretório foram preservadas.

## Falhas reproduzidas no fluxo da aplicação

### CP-01 — P2: filtros de vencimento não são aplicados

Referências: `frontend/js/app.js:53`, `:1390`, `:1407`; `src/interface/rotas/financeiro.py:25`.

O estado da tela usa `inicio` e `fim`, e `renderPayables()` envia esses nomes diretamente. A rota só lê `data_inicio` e `data_fim`.

Reprodução: contas em 15/01 e 15/02; selecionar o intervalo de fevereiro. A função real do frontend envia `inicio=2026-02-01&fim=2026-02-28`; a rota retorna as duas contas. Com os nomes esperados pela API, retorna apenas fevereiro. O erro afeta linhas, contagem e total filtrado.

Correção: mapear os campos da tela para o contrato da API e testar a integração, inclusive filtros combinados e paginação.

### CP-02 — P2: contas canceladas aumentam o “Restante filtrado”

Referências: `src/financeiro/contas_pagar.py:359`, `:378`, `:379`; `frontend/js/app.js:1408`.

O cancelamento preserva o valor histórico da conta, mas a consulta paginada soma seu restante como se ainda fosse devido. O dashboard, por comparação, exclui canceladas explicitamente (`src/interface/servidor.py:98`).

Reprodução: conta de R$ 100 cancelada e conta de R$ 200 aberta. O painel recebe R$ 300 de restante, embora apenas R$ 200 sejam exigíveis. Filtrar somente canceladas também apresenta saldo a pagar.

Correção: excluir canceladas do saldo exigível dos agregados gerais/filtrados. Preservar sua visibilidade e valores históricos, sem zerar registros no banco para ajustar a apresentação. Distinguir totais históricos de dívida atual.

### CP-03 — P2: dispensa de recorrência ignora conta manual efetiva

Referências: `src/financeiro/recorrencias.py:88`, `:91`, `:146`, `:152`.

A prévia identifica contas compatíveis pela despesa e vencimento, incluindo lançamentos manuais. Já a dispensa verifica somente contas com o mesmo `recorrencia_id`. Uma conta manual tem esse campo nulo e escapa da proteção.

Reprodução pelo pipeline POST: criar manualmente conta de R$ 200, configurar recorrência da mesma despesa/valor/vencimento e dispensar a competência. A prévia muda de `EXISTENTE` para `DISPENSADA`, mas a conta continua `ABERTA`, com R$ 200 a pagar. Isso diverge da recusa implementada para contas efetivas geradas pela própria recorrência. Não houve cancelamento nem perda do saldo; o erro é a classificação contraditória e a dispensa indevida.

Correção: usar a mesma identidade de competência na prévia e na proteção de dispensa. Verificar todas as contas efetivas da despesa/vencimento, não apenas uma linha ou o vínculo direto. Exigir tratamento explícito da conta antes de dispensar, preservando pagamentos e histórico.

### CP-04 — P3: Nova conta oferece despesa de setor inativo

Referências: `frontend/js/app.js:690`; `src/financeiro/despesas.py:10`.

O formulário filtra apenas `despesa.ativo`; inativar o setor não altera esse campo. A própria resposta de cadastros contém os setores e seus estados, mas eles não entram no filtro.

Reprodução: despesa ativa em setor inativo aparece na função real de Nova conta, executada com dependências simuladas. O backend recusa o lançamento ao salvar. A proteção de gravação funciona, mas a interface oferece uma opção inutilizável.

Correção: exigir despesa e setor ativos ao montar as opções; orientar o usuário quando não houver elegíveis. Pagamentos de contas antigas devem continuar permitidos mesmo após inativar o setor.

## Falhas reproduzidas em funções internas

Os três itens abaixo foram confirmados por chamadas diretas ao domínio. Não foi encontrado uso das funções de resumo/recálculo abaixo nas rotas atuais, e a API normal protege o cadastro contra a data inválida testada. Portanto, não se afirma que a tela atual dispara essas três falhas.

### CP-05 — P2: resumo de pagamentos lança NameError

Referência: `src/financeiro/pagamentos.py:448`, `:484`.

`resumo_conta()` inclui `valor_devido` no retorno sem definir essa variável. Qualquer chamada com conta existente falha com `NameError: name 'valor_devido' is not defined`. O cálculo local de restante também usa o valor bruto, sem descontar o desconto.

Correção: calcular devido e restante considerando descontos e pagamentos, mantendo consistência com `contas_pagar.calcular_total_pago()`; testar conta aberta, parcial, quitada com desconto e inexistente.

### CP-06 — P2: recálculo público transforma conta quitada com desconto em parcial

Referência: `src/financeiro/contas_pagar.py:468`, `:499`, `:531`.

`atualizar_status_conta()` compara pagamentos com o valor bruto, ignorando desconto; a rotina interna de `pagamentos` considera o valor líquido.

Reprodução: conta de R$ 200, pagamento de R$ 180 e desconto de R$ 20. O pagamento grava `PAGA`. Chamar o recálculo público muda para `PARCIAL` e retorna R$ 20 restantes. A consulta detalhada passa a informar simultaneamente `PARCIAL` e restante zero.

Correção: unificar a regra de recálculo pelo valor líquido e preservar canceladas. Não somar juros ao principal amortizado nem alterar os lançamentos financeiros.

### CP-07 — P2: cadastro direto aceita data impossível e centavos fracionados

Referência: `src/financeiro/contas_pagar.py:22`, `:48`, `:54`.

O domínio valida apenas presença da data e valor positivo. A chamada `cadastrar_conta(despesa_id, '2026-02-30', 100.5)` foi aceita e persistiu data impossível e valor SQLite do tipo `real`. O contrato documentado exige centavos inteiros. A rota HTTP rejeitou a data inválida no teste de controle; esta falha afeta chamadas internas/scripts que usam diretamente a função.

Correção: validar data canônica real e centavos inteiros no domínio antes de gravar, reutilizando `validar_centavos`. Rejeitar booleanos, números fracionados e valores fora dos limites com erro coerente, sem gravação parcial.

## Testes e evidências

- `python -m unittest discover -s tests -p 'test_fluxos*.py'`: 32 aprovados.
- `python -m unittest discover -s tests -p test_regressoes.py`: 24 aprovados.
- `python -m unittest discover -s tests -p test_desempenho_consultas.py`: 4 aprovados.
- Total: **60 testes Python aprovados**.
- `node tests/workflows.mjs`, `node tests/interface_visual.mjs`, `node tests/api.mjs`: todos aprovados.
- `python docs/reproduzir_auditoria_contas_pagar_2026_09_16.py`: confirmou os comportamentos backend/API descritos.
- `node docs/reproduzir_frontend_contas_pagar_2026_09_16.mjs`: executou as funções reais `renderPayables` e `openFinancialForm`, extraídas do código, com dependências simuladas; confirmou parâmetros errados e oferta de despesa de setor inativo.

As reproduções contêm asserções do comportamento defeituoso atual; não são testes de aceite da correção. Não houve teste manual em navegador/WebView nem execução da suíte completa. Python usado: `C:\Users\Cliente\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`. Nenhum banco real foi acessado pelos cenários de teste.

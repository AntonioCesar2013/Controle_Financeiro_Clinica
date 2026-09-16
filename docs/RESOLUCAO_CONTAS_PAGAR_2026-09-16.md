# Resolução da auditoria de contas a pagar — 16/09/2026

O relatório `AUDITORIA_CONTAS_PAGAR_2026-09-16.md` foi preservado como histórico. Os sete achados CP-01 a CP-07 foram reproduzidos antes da correção em banco temporário e pela execução das funções reais do frontend com dependências simuladas.

- **CP-01:** o estado `inicio`/`fim` da tela é enviado como `data_inicio`/`data_fim` à API. Busca, situação, período, paginação e totais usam os mesmos filtros.
- **CP-02:** contas canceladas continuam consultáveis e com valor histórico intacto; seu restante não compõe o saldo exigível geral ou filtrado.
- **CP-03:** a dispensa recusa qualquer conta efetiva da mesma despesa e vencimento, inclusive manual ou gerada por outra programação. A prévia mostra conflito quando há múltiplas contas efetivas ou dispensa legada incompatível.
- **CP-04:** Nova conta oferece apenas despesas ativas de setores ativos. Contas antigas continuam pagáveis.
- **CP-05/06:** resumo e recálculo de situação consideram o valor líquido após desconto, separando encargos do principal.
- **CP-07:** o cadastro direto de conta valida data ISO canônica e centavos inteiros positivos antes de gravar.

Não houve migração, alteração de registros antigos ou execução sobre `dados/clinica.db`.

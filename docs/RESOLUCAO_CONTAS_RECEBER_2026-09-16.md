# Resolução da auditoria de contas a receber — 16/09/2026

Os seis achados de `AUDITORIA_CONTAS_RECEBER_2026-09-16.md` foram reproduzidos antes das alterações, em banco temporário e com as funções JavaScript reais. O relatório original permanece como histórico.

- **CR-01:** a validação do saldo nos formulários de recebimento e pagamento compara centavos inteiros. Encargos não amortizam o principal.
- **CR-02:** o histórico recompõe `total_lancamento` para lançamentos estornados a partir do JSON original, considerando encargos ausentes como zero. O JSON preservado e os totais efetivos não mudam.
- **CR-03:** o extrato identifica devoluções estornadas com data e motivo da correção; a mesma composição segue para impressão. O total devolvido conta somente lançamentos efetivos.
- **CR-04:** Contas a receber e Mensalidades oferecem **Desconto** para cobranças com saldo disponível. O formulário mostra o saldo e o backend confirma o limite sob transação. Desconto integral sem recebimento não cria entrada de caixa ou recibo.
- **CR-05:** descontos independentes gravam um ajuste com valor e desconto anterior/novo na mesma transação da cobrança. Descontos vinculados a recebimentos continuam representados pelo próprio recebimento. A auditoria técnica de operações permanece.
- **CR-06:** `aplicar_desconto` rejeita centavos fracionários, booleanos, valores não inteiros, zero, negativos, acima do limite e acima do saldo; fecha a conexão e desfaz a transação em erro.

Não houve migração ou alteração automática de registros antigos. O novo evento de ajuste existe apenas para descontos independentes lançados a partir desta versão. A API continua recebendo reais e convertendo para centavos uma vez; não foi criado campo de motivo, preservando os consumidores atuais. Para aplicar o código, reinicie o sistema.

# Correções do fluxo de trabalho — 12/09/2026

## 1. Estoque e classificação dos itens

A troca entre produto e serviço é recusada se houver estoque ou qualquer histórico de venda/movimentação, mesmo quando o estoque atual for zero. Nesse caso, deve-se cadastrar outro item. Isso preserva a reposição correta em estornos. Itens sem estoque nem histórico podem mudar de classificação.

Não há ajuste automático de possíveis inconsistências anteriores nesta atualização.

## 2. Acerto no encerramento

Em **Internações → Encerrar**, informe a data e consulte **Conferir prévia**. Para particulares, escolha expressamente:

- **Manter cobranças contratadas**: preserva o que continua devido.
- **Dispensar mensalidades com vencimento após a saída**: zera integralmente essas mensalidades, preservando acolhimento e cobranças vencidas até a data da saída. Não presume proporcionalidade nem multa contratual.

Convênios são recalculados pelas diárias utilizadas, incluindo parcelas de prorrogação. A prévia mostra valores anteriores/novos, descontos, recebido líquido, devolução necessária e dívida restante. Reduções de descontos exigem confirmação no formulário. Alterações dos valores ou do saldo da carteira após a prévia exigem nova conferência.

Recebimentos acima do valor recalculado devem ser devolvidos antes de concluir. A baixa da internação, os ajustes e o registro do acerto são gravados juntos. Os vencimentos originais ficam preservados.

O saldo da carteira é mostrado separadamente. A saída do residente não apaga dívida nem saldo da carteira e não registra automaticamente pagamento ou devolução. O acerto guarda essa posição para consulta histórica no banco.

## 3. Devoluções efetivas

Em **Contas a receber → Histórico de recebimentos → Devolver valor**, informe principal, eventuais multas/juros devolvidos, data, forma, motivo e comprovante. Registre somente dinheiro efetivamente devolvido.

O recebimento e o recibo originais são preservados. A devolução entra como saída na data informada; o saldo da cobrança usa o recebimento líquido. O recibo sinaliza devoluções posteriores. Extratos e histórico exibem as devoluções. Um recebimento com devolução não pode ser apagado ou alterado.

Em **Carteiras → selecionar residente → Devolver saldo**, a devolução reduz o saldo e aparece no histórico da carteira, inclusive se ela estiver inativa. Não é contabilizada como compra da cantina nem como despesa da clínica. O valor não pode exceder o saldo; a data não pode anteceder a última movimentação válida da carteira.

Datas futuras e devoluções acima dos valores disponíveis são recusadas. Reenvios com a mesma identificação da operação não duplicam lançamentos.

## 4. Despesas recorrentes

Em **Despesas**, marque a despesa como recorrente e use **Programar**. Defina valor, primeiro vencimento, fim e intervalo de 1 a 12 meses. Depois use **Gerar contas**, informando até qual data gerar.

A geração é por comando explícito, sem tarefa agendada em segundo plano. O dia original é mantido: 31/01 gera 28/02 e 31/03. Contas existentes da mesma despesa e vencimento, inclusive manuais ou canceladas, são preservadas e não são recriadas. O resultado informa quantas foram criadas e quantas já existiam.

**Encerrar programação** impede novas gerações; não apaga contas já geradas. Para mudar os parâmetros, encerre a programação anterior e cadastre outra. Apenas uma programação ativa por despesa é permitida.

## 5. Prorrogação

Em **Internações → Prorrogar**, informe o novo período total e o motivo. O limite é 120 meses. Particular usa a mensalidade contratada; convênio acrescenta diárias a partir do dia seguinte ao término anterior. Não é cobrado novo acolhimento. Social continua sem cobrança; voluntário já não tem prazo determinado.

Parcelas, descontos e recebimentos anteriores são preservados. Uma prorrogação que coincida com outra internação é recusada. Saídas antecipadas e agendamentos cancelados não podem ser prorrogados. Telas desatualizadas e reenvios não duplicam parcelas.

## 6. Atrasos

Contas parcialmente pagas agora podem informar simultaneamente `PARCIAL`, `ATRASADA` e a quantidade de dias em atraso. Cobranças quitadas ou sem saldo não acumulam dias de atraso. Contas a receber mostra pagamento e prazo em colunas separadas.

## Atualização e validação

As migrações `financeiro:6` e `cantina:2` são aplicadas automaticamente na próxima inicialização. Não reescrevem os recebimentos existentes. Fechamentos anteriores sem novas devoluções mantêm a assinatura original.

Validação automatizada em bancos temporários: regressões existentes, regras de negócio, rotas, concorrência, reenvios, migrações repetíveis e formulários. Não foram feitos lançamentos de teste no banco real da clínica. Login, permissões e backup ficaram fora desta alteração.

## Complementos da segunda revisão

- Recebimentos e pagamentos efetivos recusam datas futuras. Um recebimento feito hoje para uma cobrança que vence depois continua permitido.
- Vendas futuras são recusadas. A cantina consulta a vigência histórica da internação na data da venda, incluindo cancelamentos, encerramentos e prorrogações; saldo negativo da carteira continua permitido.
- Devoluções lançadas por engano podem ser corrigidas pelo histórico. O original permanece marcado como estornado, com data e motivo. Na carteira, o saldo retorna; no tratamento, cobrança, caixa, extrato e recibo são recalculados. A correção é bloqueada quando faria os recebimentos ultrapassarem um contrato já ajustado.
- O responsável gravado em cada internação permanece como dado do contrato. O contato principal atual é escolhido separadamente na tela do residente. Agendamentos não substituem essa escolha. Cadastros antigos com mais de um principal aparecem como “REVISAR” e exigem seleção explícita; a migração não escolhe por conta própria.
- Novas contas manuais e recorrentes usam a mesma validação e recusam despesas ou setores inativos. Contas antigas continuam disponíveis para consulta e pagamento.

As migrações adicionais `financeiro:7` e `cadastros:2` são aplicadas na próxima inicialização. Elas acrescentam o histórico de correções e a proteção contra novos contatos principais duplicados, sem resolver automaticamente ambiguidades legadas.

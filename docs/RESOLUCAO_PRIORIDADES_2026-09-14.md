# Resolução das prioridades identificadas em 13/09/2026

Este registro complementa `ANALISE_SISTEMA_2026-09-13.md`, que permanece preservado
como diagnóstico histórico.

## Integração das gravações

O cliente envia `Idempotency-Key` em todos os comandos de negócio protegidos pelo
servidor. Uma operação em andamento compartilha a mesma promessa entre cliques
repetidos. Se a resposta for perdida, o cliente consulta o resultado pela chave. Uma
confirmação persistida é recuperada sem repetir o lançamento. Se o servidor confirmar
que a chave não chegou, o cliente cancela explicitamente a tentativa antes de informar
que nada foi realizado. Se nem a consulta for possível, o estado permanece
desconhecido e a mesma chave é reutilizada no próximo envio com os mesmos dados.

Rotas de autenticação, backup e sincronização mantêm o tratamento próprio. Cancelar a
espera de uma requisição não cancela nem estorna a gravação correspondente.

## Datas de movimentos efetivos

Créditos de carteira, correções de crédito e ajustes de estoque recusam data posterior
ao dia atual antes de alterar saldo ou histórico. A interface limita esses três campos
ao dia atual e o backend mantém a validação obrigatória. Internações agendadas,
vencimentos e preços com vigência futura continuam permitidos.

Registros antigos não são modificados automaticamente. Para identificar possíveis
inconsistências, consulte movimentos de carteira do tipo `CREDITO` e movimentos de
estoque cuja `data_movimentacao` seja posterior à data atual. Cada caso deve ser
conferido com o comprovante e corrigido pelos fluxos existentes; não apague linhas
diretamente no banco.

## Backup e recuperação

O catálogo reúne o formato legado na pasta histórica e o formato atual na pasta
configurada. Ambos podem ser restaurados pelo comando existente. O arquivo é validado
antes da restauração, o banco atual recebe uma cópia preventiva e uma trava entre
processos impede recuperação enquanto o sistema estiver aberto.

O automático permanece desativado por padrão, usa intervalo padrão de seis horas e
depende do processo aberto. Não existe retenção ou exclusão automática. A tela separa
o último snapshot local íntegro dos últimos envios bem-sucedidos para R2 e Drive e
indica estados desativado, nunca concluído, atrasado e em dia.

# Correções da auditoria final — 21/09/2026

Este registro complementa, sem substituir, `AUDITORIA_FINAL_PRODUCAO_2026-09-21.md`.

## Correções concluídas

- O painel de backup funciona no modo local de administrador único sem sessão. A
  rota exige cliente e servidor no loopback; comandos mantêm verificação de origem,
  corpo JSON e armazenamento seguro das credenciais.
- A transferência de item administrativo exige escolha explícita do setor. A tela
  mostra origem e destino e bloqueia o fluxo quando não existe setor ativo.
- A movimentação distingue quantidade movimentada de saldo final do ajuste, mostra
  o saldo previsto para entrada, saída, ajuste e baixa e avisa quando uma baixa total
  também inativará o item.
- `valor_aquisicao` segue o contrato monetário comum: aceita número JSON ou texto
  decimal, inclusive zero, é convertido uma única vez para centavos e recusa valores
  negativos ou inválidos.

## Pendência operacional do achado 1

Para configurar o backup real ainda é necessário informar uma pasta absoluta e
acessível destinada às cópias. Recomenda-se outro dispositivo, unidade externa ou
pasta sincronizada cuja disponibilidade tenha sido confirmada. Também é necessário
definir o intervalo desejado e se haverá R2 ou Google Drive. Nenhum destino externo
foi presumido ou ativado nesta correção.

Depois de autorizado o destino, deve-se ativar o backup, gerar uma cópia atual e
restaurá-la em um banco separado. A liberação para produção continua pendente dessa
prova de recuperação e da homologação manual final descrita no relatório original.

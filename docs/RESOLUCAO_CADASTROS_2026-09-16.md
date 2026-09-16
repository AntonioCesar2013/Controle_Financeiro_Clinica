# Resolução da auditoria de cadastros — 16/09/2026

O relatório `AUDITORIA_CADASTROS_2026-09-16.md` foi preservado como histórico. Seus sete achados foram reproduzidos e corrigidos:

1. O formulário e a API normalizam o período do voluntário para zero, eliminam valores de modalidades ocultas e não geram cobranças. As demais modalidades continuam exigindo período positivo.
2. A edição do responsável contratual consulta a internação, seleciona seu vínculo atual e mostra quando ele está inativo. O contato principal permanece independente. A ação só fica disponível para internações ativas ou agendadas.
3. Cadastros duplicados deixam explícito que os dados digitados não foram gravados e oferecem a abertura da edição do registro existente.
4. Identificadores `PENDENTE-` já persistidos podem ser mantidos ao editar outros dados ou substituídos por documento numérico válido. A edição não aceita criar outro identificador pendente.
5. O dia de uma saída registrada é exclusivo para a internação anterior no cadastro e na prorrogação, conforme a consulta de vigência. O término natural sem saída registrada continua inclusivo.
6. Booleanos admitidos na API são normalizados para 0/1. Valor inválido aponta o campo e não gera gravação.
7. Nova internação oferece somente responsáveis ativos e orienta cadastrar ou reativar quando não houver elegíveis.

As regressões usam bancos temporários. Não houve execução sobre `dados/clinica.db`, migração ou alteração de dados reais.

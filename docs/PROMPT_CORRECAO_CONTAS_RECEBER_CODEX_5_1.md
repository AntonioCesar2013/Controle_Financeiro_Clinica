# Prompt de correção de contas a receber — Codex 5.1

No projeto `C:\Projetos\Controle_Financeiro_Clinica`, implemente e valide as correções da auditoria `docs/AUDITORIA_CONTAS_RECEBER_2026-09-16.md`.

Leia as instruções AGENTS.md aplicáveis e os scripts `docs/reproduzir_auditoria_contas_receber_2026_09_16.py` e `docs/reproduzir_frontend_contas_receber_2026_09_16.mjs`. Confira o estado do Git e preserve as alterações anteriores de cadastros e contas a pagar, inclusive as existentes em `frontend/js/app.js` e validação compartilhada. Não substitua arquivos inteiros por versões antigas.

Reproduza os achados antes de corrigir. Se algum já estiver resolvido, registre a evidência. As asserções dos scripts da auditoria confirmam defeitos atuais; crie regressões que exijam o comportamento correto.

Implemente:

1. **CR-01 — Comparação monetária frontend:** usar centavos inteiros em `updateSettlementRemaining`. Saldo de R$ 0,30 com R$ 0,10 recebidos + R$ 0,20 de desconto deve ser aceito e mostrar zero restante. R$ 0,31 sobre saldo R$ 0,30 deve continuar recusado. Verificar que editar os campos remove o erro anterior e que juros não amortizam principal. A função é compartilhada com contas a pagar: cobrir ambos os formulários.
2. **CR-02 — Total de estornados:** normalizar campos derivados dos registros de histórico, incluindo `total_lancamento = valor + multa_juros`, sem alterar JSON histórico original nem reincluir estornos no caixa. Testar recebimento de R$ 10 + R$ 1,50 de encargos: depois do estorno, o histórico deve mostrar total original R$ 11,50 com situação ESTORNADO, enquanto o caixa deixa de computá-lo. Cobrir encargos ausentes em registros legados e o consumidor compartilhado de pagamentos de saída.
3. **CR-03 — Devoluções no extrato:** identificar devoluções estornadas com situação, motivo e data de correção, tanto no documento em tela quanto no conteúdo de impressão. Manter a linha histórica. Devolução de R$ 4 registrada por engano e estornada deve aparecer como estornada e contribuir com zero ao total efetivo. Testar mistura de devoluções efetivas, parciais e estornadas.
4. **CR-04 — Desconto independente:** disponibilizar nas telas Contas a receber e Mensalidades a ação de desconto já existente, respeitando elegibilidade e seleção da cobrança. Permitir desconto integral e desconto sobre saldo parcialmente recebido, até o limite do saldo atual. Não criar recebimento fictício, movimentação de caixa ou recibo por desconto. Não liberar valor zero na rota de recebimento como atalho. Preservar validações de status e proteção contra alterações concorrentes.
5. **CR-05 — Histórico do desconto:** registrar descontos independentes em `ajustes_cobrancas` na mesma transação da atualização, com valores anterior/novo e motivo adequado. Se incluir campo de motivo na API/formulário, tratar compatibilidade dos consumidores existentes conscientemente. Exibir o ajuste no histórico da cobrança. Reenvio com a mesma chave deve produzir um único desconto e um único evento; erro deve desfazer ambos. Não duplicar eventos de descontos concedidos por recebimentos nem afirmar que a auditoria técnica geral estava ausente.
6. **CR-06 — Validação no domínio:** `aplicar_desconto` deve aceitar somente centavos inteiros positivos dentro dos limites monetários e do saldo disponível. Reutilizar `validar_centavos`; rejeitar `0.5`, booleanos, tipos inválidos, zero, negativos e valores fora do limite antes de gravar. A API continua recebendo reais e convertendo uma única vez. Garantir rollback e fechamento da conexão em todos os caminhos; não alterar dados legados automaticamente.

Restrições:

- Use somente bancos temporários, seguindo as fixtures com patch de `src.infraestrutura.banco.CAMINHO_BANCO`. Não executar populadores, `src/test.py`, nem testes sobre `dados/clinica.db`.
- Não alterar dinheiro ou dados reais, apagar histórico, criar migração destrutiva, fazer commit/push/publicação ou reativar permissões.
- Preserve arquitetura modular, atomicidade, idempotência, bloqueios de períodos fechados, conciliação e as regras existentes de devolução/estorno. Desconto não equivale a recebimento, e estorno de devolução não representa nova entrada de dinheiro.
- Preserve os dados de recibos já emitidos. Esta auditoria não autoriza reescrever documentos históricos.

Testes e entrega:

- Criar regressões backend/API e de comportamento frontend para os seis itens. Testes que só verificam presença de strings no código não bastam para soma monetária, elegibilidade de ações e renderização dos históricos.
- Executar `python -m unittest discover -s tests -p 'test_fluxos*.py'`, `python -m unittest discover -s tests -p test_regressoes.py`, novos testes e testes de operações/API se modificar o pipeline ou idempotência.
- Executar `node tests/documentos.mjs`, `node tests/workflows.mjs`, `node tests/api.mjs`, `node tests/datas.mjs` e novos testes frontend. Ao tocar código compartilhado, executar também os testes de contas a pagar/cadastros existentes.
- A auditoria usou `C:\Users\Cliente\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`. Use um interpretador funcional disponível se a `.venv` não iniciar, sem reinstalar desnecessariamente.
- Revisar o diff final e entregar correções, arquivos alterados, comandos/resultados de testes e limitações. Não afirmar teste manual em navegador/WebView sem realizá-lo.

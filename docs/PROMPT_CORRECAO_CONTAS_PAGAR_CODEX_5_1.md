# Prompt para correção de contas a pagar — Codex 5.1

No projeto `C:\Projetos\Controle_Financeiro_Clinica`, implemente e teste as correções da auditoria `docs/AUDITORIA_CONTAS_PAGAR_2026-09-16.md`.

Leia AGENTS.md aplicáveis, o relatório e os scripts `docs/reproduzir_auditoria_contas_pagar_2026_09_16.py` e `docs/reproduzir_frontend_contas_pagar_2026_09_16.mjs`. Confira o estado do Git: há alterações de outra revisão de cadastros, inclusive em `frontend/js/app.js` e validação compartilhada. Preserve-as e integre somente os ajustes necessários a contas a pagar. Não reverta arquivos inteiros.

Reproduza cada falha antes de corrigir. Se já estiver resolvida, documente a evidência. Os scripts de auditoria confirmam o comportamento defeituoso; crie testes de regressão com o comportamento correto, não mantenha a falha apenas para satisfazer essas asserções.

Implemente os sete itens:

1. **CP-01 — Filtro de vencimento:** mapear `inicio`/`fim` do estado frontend para `data_inicio`/`data_fim` da API. Testar janeiro/fevereiro com seleção de fevereiro, limites inclusivos, filtro parcial, combinação com busca/status e mudança de página. Os registros, contagem e totais devem representar o mesmo filtro. O teste deve exercitar o contrato frontend/API, não apenas chamar a consulta Python com parâmetros corretos.
2. **CP-02 — Canceladas nos totais:** retirar contas canceladas do saldo exigível nos totais gerais e filtrados, preservando valores históricos e a consulta de canceladas. R$ 100 cancelados + R$ 200 abertos devem resultar em R$ 200 a pagar; somente canceladas devem resultar em zero exigível. Não zerar `valor`/`desconto` no banco. Manter consistência com o dashboard e deixar clara a distinção entre valor histórico e dívida.
3. **CP-03 — Dispensa indevida:** harmonizar prévia e dispensa de recorrência pela despesa/vencimento, incluindo contas manuais e de outra programação. Recusar dispensa enquanto houver conta efetiva correspondente. Consultar todas as correspondências relevantes, preservando conflitos explícitos em vez de ocultá-los. Não cancelar, vincular ou alterar pagamentos silenciosamente. Testar conta manual aberta, paga/parcial, conta gerada, cancelada e competência sem conta; garantir que a recusa não grave dispensa.
4. **CP-04 — Setor inativo:** ao criar conta, oferecer apenas despesas ativas de setores ativos. Se não houver elegíveis, orientar cadastrar/reativar. Manter a validação backend contra mudanças concorrentes e permitir pagamento/estorno de contas antigas de setor inativado conforme as regras existentes.
5. **CP-05 — Resumo interno:** corrigir `pagamentos.resumo_conta`, que referencia `valor_devido` sem definição e calcula restante sem desconto. Alinhar os valores com a consulta detalhada. Testar inexistente, aberta, parcial e quitada com desconto. Não afirmar falha de rota atual: o defeito foi reproduzido na chamada direta.
6. **CP-06 — Recálculo interno:** corrigir `contas_pagar.atualizar_status_conta` para considerar desconto, preferencialmente compartilhando a regra com a rotina de pagamentos. Conta de R$ 200 quitada com R$ 180 pagos + R$ 20 de desconto deve permanecer PAGA com restante zero após recálculo. Preservar CANCELADA, pagamentos, estornos e separação entre principal e encargos. Testar também pagamento parcial e estorno do pagamento com desconto.
7. **CP-07 — Validação no domínio:** validar data canônica real e centavos inteiros positivos em `cadastrar_conta`, usando as validações compartilhadas apropriadas. Recusar `2026-02-30`, formato não canônico, booleanos, 100.5 centavos, zero/negativos, nulos e valores fora do limite. Não arredondar/truncar silenciosamente. A API continua recebendo reais e convertendo uma única vez; chamadas internas continuam usando centavos. Não modificar dados legados automaticamente.

Restrições:

- Trabalhar somente com bancos temporários, seguindo as fixtures que substituem `src.infraestrutura.banco.CAMINHO_BANCO`. Não acessar/gravar `dados/clinica.db`, executar populadores ou `src/test.py`.
- Não criar migração destrutiva, apagar histórico, efetuar pagamentos reais, commit, push ou publicação.
- Preservar arquitetura modular, atomicidade, idempotência e bloqueios de períodos financeiros fechados. Não reativar permissões ou expandir o trabalho para outros módulos.
- Não confundir o erro da dispensa com autorização para perdoar uma dívida efetiva. Exigir o tratamento explícito da conta nos fluxos existentes.

Validação mínima:

- Criar regressões para todos os itens, backend/API e comportamento frontend. Não se limitar a procurar strings no código.
- Executar `python -m unittest discover -s tests -p 'test_fluxos*.py'`, `python -m unittest discover -s tests -p test_regressoes.py`, `python -m unittest discover -s tests -p test_desempenho_consultas.py` e os novos testes.
- Executar `node tests/workflows.mjs`, `node tests/interface_visual.mjs`, `node tests/api.mjs` e os novos testes frontend. Se tocar código compartilhado de cadastros, executar também `node tests/cadastros.mjs` e os testes Python de cadastros presentes no projeto. Executar testes de operações/API se alterar esse pipeline.
- Se a `.venv` não iniciar, usar um interpretador funcional disponível sem reinstalar ou mudar o ambiente desnecessariamente. A auditoria utilizou `C:\Users\Cliente\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
- Revisar o diff, relatar correções, arquivos modificados, resultados de testes e limitações. Não afirmar teste manual em navegador se ele não ocorreu.

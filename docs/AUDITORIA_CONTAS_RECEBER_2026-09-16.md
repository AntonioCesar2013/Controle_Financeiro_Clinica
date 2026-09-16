# Auditoria de contas a receber — 16/09/2026

Escopo: cobranças, mensalidades, recebimentos, descontos, estornos, devoluções, histórico, extrato do residente e recibos. Revisão de domínio, API e frontend, com reproduções em bancos temporários e execução de funções JavaScript reais com dependências simuladas. Não houve teste manual em navegador/WebView, correção funcional ou uso de dados reais. Alterações anteriores de cadastros e contas a pagar foram preservadas.

## CR-01 — P2: formulário rejeita recebimento e desconto cuja soma é exata

Referências: `frontend/js/app.js:733`, função `updateSettlementRemaining`; `frontend/js/utils/masks.js`, `currencyValue`.

O formulário subtrai valores monetários usando números decimais JavaScript e considera qualquer resultado negativo um excesso. Exemplo reproduzido: saldo R$ 0,30, recebimento R$ 0,10 e desconto R$ 0,20. A subtração resulta em aproximadamente -0,0000000000000000278 e aplica `setCustomValidity` com “O valor e o desconto não podem ultrapassar o saldo restante”.

A API recebeu a mesma combinação em um teste de controle e quitou corretamente a cobrança com saldo zero. Portanto, o erro está na validação da interface. A função é compartilhada com pagamentos de saída.

Correção: realizar a comparação em centavos inteiros, sem liberar excesso real. Testar soma exata, recebimento parcial, excesso de um centavo e retirada do erro após editar os campos. Não usar uma tolerância que aceite valores indevidos.

## CR-02 — P2: histórico mostra R$ 0,00 no total de recebimento estornado

Referências: `src/financeiro/estornos.py:23`; `src/financeiro/recebimentos.py`, `buscar_pagamentos`; `frontend/js/app.js`, `openFinancialHistory`; `frontend/js/utils/formatters.js:7`.

Recebimentos ativos retornam o campo derivado `total_lancamento`. Os estornados são recuperados do JSON das colunas originais, que não contém esse campo. A tabela usa `total_lancamento` e o formatador converte a ausência em zero.

Reprodução: principal R$ 10,00 e encargos R$ 1,50; depois de estornar, a rota de histórico mantém principal/encargos, mas omite o total. O renderizador mostra R$ 0,00 em “Total recebido”, em vez de R$ 11,50. Não houve perda do valor original no banco; é uma falha de composição/apresentação. O helper também é compartilhado com contas a pagar.

Correção: fornecer os mesmos campos derivados para registros ativos e estornados, preservando a indicação de estorno e sem reincluir o lançamento nos totais efetivos.

## CR-03 — P2: extrato apresenta devolução estornada sem identificá-la

Referências: `src/interface/extrato_residente.py:34`, `:66`; `frontend/js/components/resident-documents.js`, `statementBody`.

A API inclui devoluções efetivas e estornadas no extrato, com situação e motivo de correção. O resumo exclui corretamente as estornadas. Porém, a tabela do documento mostra apenas data, total, motivo original e documento, omitindo situação e correção.

Reprodução: registrar devolução de R$ 4,00 por engano e estorná-la. O extrato retorna total efetivo devolvido zero, mas apresenta a linha de R$ 4,00 como uma devolução sem ressalva. A composição usada para impressão contém o mesmo problema.

Correção: preservar a linha histórica com indicação clara de ESTORNADA e motivo/data da correção; manter o total efetivo zero. A tela de Histórico da cobrança já distingue devoluções efetivas e estornadas e pode orientar a consistência visual.

## CR-04 — P2: desconto independente/integral não tem ação acessível na tela

Referências: `frontend/js/app.js:680`, `:749`, `:1347`, `:1370`; `src/financeiro/recebimentos.py`, validação de valor; `src/financeiro/cobrancas.py:235`.

Existe definição de formulário e rota para aplicar desconto sem recebimento, mas Contas a receber e Mensalidades só oferecem Receber e Histórico. Não há gatilho `data-kind="desconto"` no frontend. No formulário de recebimento, valor zero é recusado, mesmo que o desconto cubra todo o saldo.

Reprodução: cobrança de R$ 100; tentar quitar exclusivamente por desconto. A rota de recebimento recusa zero; a rota própria de desconto aceita R$ 100 e resulta em DESCONTADA, demonstrando que a regra existe, mas não está acessível pela interface normal. A ausência do gatilho foi verificada no código e no HTML gerado pela função real da tela.

Correção: disponibilizar a ação existente de desconto independente para cobranças elegíveis, incluindo desconto integral. Não criar recebimento fictício, entrada em caixa ou recibo para representar um desconto.

## CR-05 — P2: desconto independente não aparece no histórico de ajustes da cobrança

Referências: `src/financeiro/cobrancas.py:235`, `:310`; `src/financeiro/estornos.py:36`; `frontend/js/app.js`, seção “Ajustes da cobrança” em `openFinancialHistory`.

Aplicar desconto independente atualiza `cobrancas.desconto/status`, mas não registra a alteração em `ajustes_cobrancas`. Diferentemente dos ajustes de encerramento, esse evento não aparece na consulta específica de ajustes usada pela tela.

Reprodução pelo pipeline POST: desconto de R$ 10 em uma cobrança de R$ 300 reduz o devido para R$ 290, enquanto `historico_ajustes` retorna lista vazia. Existe auditoria técnica geral do POST em `operacoes`; não se afirma ausência total de rastreabilidade. A lacuna está no histórico financeiro acessível da cobrança e na falta de um evento com valores anterior/novo.

Correção: registrar o ajuste na mesma transação do desconto, com valores anterior/novo e motivo identificável. Preservar a idempotência para não duplicar o evento em reenvio. Não duplicar eventos de desconto já representados por recebimentos.

## CR-06 — P2: função interna de desconto aceita fração de centavo

Referências: `src/financeiro/cobrancas.py:235`, `:274`, `:297`; `src/financeiro/moeda.py`, `validar_centavos`.

`aplicar_desconto` verifica somente se o valor é positivo e cabe no saldo; não exige inteiro nem rejeita booleanos. A chamada direta com `0.5` foi aceita, deixando o desconto persistido como `1000.5`, tipo SQLite `real`, após um desconto anterior de 1000 centavos.

Este caso foi reproduzido por chamada direta ao domínio. A API normal converte reais para centavos inteiros; não se atribui essa gravação fracionada ao formulário atual.

Correção: validar centavos inteiros e limites antes de abrir a transação, reutilizando a validação monetária comum. Rejeitar frações, booleanos e tipos inválidos sem truncar ou arredondar silenciosamente; garantir fechamento/rollback em erros.

## Evidências e limites

- `python -m unittest discover -s tests -p 'test_fluxos*.py'`: 32 testes aprovados.
- `python -m unittest discover -s tests -p test_regressoes.py`: 24 testes aprovados.
- Total: **56 testes Python aprovados**.
- `node tests/documentos.mjs`, `node tests/workflows.mjs`, `node tests/api.mjs`, `node tests/datas.mjs`: todos aprovados.
- `python docs/reproduzir_auditoria_contas_receber_2026_09_16.py`: confirmou histórico sem total, devolução estornada no payload do extrato, desconto ausente dos ajustes, desconto fracionário e contraste entre as rotas de recebimento/desconto. Confirmou também que a API aceita corretamente a soma exata de R$ 0,10 + R$ 0,20.
- `node docs/reproduzir_frontend_contas_receber_2026_09_16.mjs`: confirmou a rejeição decimal, total zero no renderizador, devolução estornada sem identificação no documento e ausência de ação de desconto.

Os scripts de reprodução contêm asserções do comportamento defeituoso atual, não critérios de aceite da correção. Foram usados bancos temporários e o Python em `C:\Users\Cliente\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`. A suíte completa não foi executada. A aprovação dos testes existentes não cobre os seis cenários adicionais encontrados.

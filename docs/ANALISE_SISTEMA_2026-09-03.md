# Análise do sistema — 03/09/2026

> Atualização após a análise: o usuário confirmou que vendas com saldo negativo
> são uma regra intencional, com cobrança posterior dos responsáveis; o item 1
> abaixo deixa de ser considerado defeito. As correções dos demais problemas
> foram implementadas, com regressões em `tests/test_regressoes.py` e
> `tests/datas.mjs`. O texto abaixo preserva os achados anteriores às correções.
> O script exploratório temporário foi substituído pelos testes automatizados.

O sistema tem uma base adequada para uma aplicação local simples: backend separado por domínio, SQLite, valores do financeiro em centavos, geração transacional de internação com cobranças, histórico de preços e movimentos de estoque, estorno de cupons e backup diário. A recomendação é corrigir a consistência das operações antes de ampliar funcionalidades; não há necessidade imediata de reescrever a aplicação ou trocar o banco.

## Escopo e evidências

Análise do código de cadastros, internações, financeiro, cantina, relatórios, infraestrutura e integração com o frontend. Login excluído do escopo. Reproduções executadas com banco SQLite novo, temporário e dados fictícios, por meio de `tmp/analise_isolada.py`. O banco da clínica não foi usado nem alterado. O código da aplicação não foi modificado.

Os testes foram das funções de negócio; não equivalem a uma validação visual completa no WebView2, teste do leitor físico ou impressão A4. Não executei o teste manual/populadores que alteram os dados da instalação. O Python do ambiente virtual retornou acesso negado neste ambiente de análise, então usei o runtime disponível no Codex; isso não foi classificado como defeito do iniciador da aplicação.

## Problemas prioritários

### 1. Cantina permite compra acima do saldo — alta

**Reproduzido:** carteira com R$ 10,00 aceitou compra de R$ 15,00 e terminou com saldo de −R$ 5,00. Isso contraria a regra documentada no README de impedir compras sem saldo.

**Causa:** `src/cantina/vendas.py`, funções `registrar_compra` e `registrar_venda`, debitam o saldo sem validar suficiência. O frontend, em `refreshCanteenCart`, apenas destaca o saldo negativo; o botão depende de residente e itens selecionados.

**Sugestão:** conferir saldo dentro da mesma transação que grava venda e estoque; recusar integralmente a operação quando insuficiente. Se vender a prazo for uma decisão desejada, tornar a regra explícita, com limite e controle de dívida, e atualizar a documentação.

### 2. Recebimento aceita data impossível e prejudica consultas — alta

**Reproduzido:** um recebimento de quitação com data `2026-02-30` foi salvo com sucesso. Depois, `listar_cobrancas_consolidadas()` levantou `ValueError` ao interpretar a data.

**Impacto:** a consulta de contas a receber e o dashboard, que usa a mesma consulta, podem falhar por causa de um único lançamento inválido. O campo de data do navegador reduz a chance no uso normal, mas a API não valida esse dado e futuras importações também podem atingir a função.

**Referência:** `src/financeiro/recebimentos.py:11`; conversão posterior em `src/financeiro/contas_receber.py`.

**Sugestão:** validar data ISO estrita antes de gravar, como já ocorre nos pagamentos de saída. Conferir dados existentes em uma etapa separada antes de qualquer correção. A mensagem de pagamento acima do restante também apresenta centavos como reais e deve dividir o valor por 100.

### 3. Encerramento de convênio pode produzir valor devido negativo — alta

**Reproduzido:** diária de R$ 100,00, acolhimento em 01/08, desconto de R$ 2.000,00 na competência de agosto e encerramento em 10/08. A cobrança passou a R$ 1.000,00, preservando desconto de R$ 2.000,00 e status `ABERTA`: valor devido de −R$ 1.000,00.

**Causa:** `src/financeiro/cobrancas.py:49` altera o valor sem reconciliar desconto/status. Cobranças com qualquer recebimento são ignoradas integralmente pelo ajuste, inclusive as parcialmente recebidas, e precisam de uma regra explícita.

**Sugestão:** calcular o acerto completo, apresentar diferenças e recalcular valor, desconto e status de forma consistente. Não reduzir desconto nem apagar recebimentos silenciosamente. O encerramento e seu acerto financeiro também devem compartilhar uma transação: atualmente o encerramento é confirmado antes do ajuste e uma falha intermediária pode deixá-los divergentes.

### 4. Data futura de encerramento inativa o residente imediatamente — média

**Reproduzido:** internação atual encerrada com data de dez dias à frente deixou o residente inativo no mesmo instante.

**Causa:** `encerrar_internacao` aceita data futura, enquanto `sincronizar_status_residentes`, em `src/cadastros/internacoes.py:24`, considera qualquer `encerrada_em` preenchida como encerramento já efetivado.

**Impacto:** bloqueia antecipadamente operações que exigem residente ativo, incluindo compras na cantina.

**Sugestão:** para o sistema simples, recusar encerramento futuro. Se houver necessidade de agendamento, separar data prevista de alta efetiva e comparar a data antes de inativar.

### 5. Correção de crédito bloqueia ajustes financeiramente válidos — média

**Reproduzido:** com saldo atual de R$ 50,00 e crédito original de R$ 100,00 já parcialmente consumido, corrigir o crédito para R$ 120,00 foi recusado. O saldo correto seria R$ 70,00.

**Causa:** `src/cantina/vendas.py:194` exige que o saldo permita remover o crédito antigo antes de considerar o novo.

**Sugestão:** validar o saldo final `saldo atual − crédito antigo + crédito novo`, preservando o histórico de correção na mesma transação.

### 6. Relatório de despesas inclui contas canceladas — média

**Reproduzido:** uma conta cancelada de R$ 100,00 continuou no total previsto e na quantidade de lançamentos do setor.

**Referência:** consulta de `despesas_setor`, `src/interface/relatorios.py:61`.

**Sugestão:** excluir canceladas dos compromissos previstos ou apresentá-las em coluna separada, sem somá-las ao total válido.

O mesmo relatório filtra pelo vencimento da conta, mas soma pagamentos de qualquer data. No teste, o relatório de agosto mostrou como pago R$ 100,00 efetivamente pagos em setembro. Essa é uma **ambiguidade de critério**, não necessariamente erro se a intenção for mostrar a situação atual das contas vencidas no período. Explicitar isso no título/legenda ou oferecer dois critérios: pagamentos realizados no período e situação das contas por vencimento. Hoje a comparação com o fluxo de caixa pode induzir uma interpretação incorreta.

### 7. Relatório de estoque apresenta preço futuro como atual — média

**Reproduzido:** preço vigente de R$ 15,00 e preço agendado de R$ 99,00 para daqui a 30 dias. O catálogo mostrou R$ 15,00, mas o relatório de estoque mostrou R$ 99,00.

**Causa:** `src/interface/relatorios.py:122` busca o último preço ativo sem limitar a data de vigência. O catálogo e a venda já usam esse limite.

**Sugestão:** compartilhar a consulta de preço vigente entre catálogo, caixa e relatório.

### 8. Datas do frontend usam UTC — média, identificado no código

`frontend/js/app.js` usa repetidamente `new Date().toISOString().slice(0, 10)` para datas padrão e classificação de vencimento. Em São Paulo, às 21h, a data UTC já corresponde ao dia seguinte.

**Impacto:** os formulários podem sugerir amanhã e a tela pode classificar vencimentos antes do backend, que usa a data local.

**Sugestão:** criar uma única função para a data local de operação e reutilizá-la. O problema foi identificado por inspeção do código; não foi simulado no WebView2.

## Melhorias funcionais próximas

- **Contrato e cobranças:** o cadastro aceita valor de contrato independente do acolhimento e das mensalidades. No teste, contrato de R$ 1.000,00 gerou R$ 700,00 em cobranças. Definir se devem coincidir; se sim, calcular automaticamente e mostrar o total antes de salvar. Se forem conceitos distintos, explicar a diferença na tela.
- **Cobranças zeradas:** cadastro particular com valores zero gerou três cobranças `ABERTA`, mas o recebimento recusa valor devido zero. Não gerar essas obrigações ou tratá-las como sem valor a receber, com regra de status definida.
- **Estornos financeiros:** as funções de exclusão realmente apagam recebimentos/pagamentos, embora a interface diga “Estornar”. Existe auditoria da requisição, mas ela guarda os dados enviados — nessas ações, principalmente o ID — e não preserva integralmente o lançamento apagado. Adotar cancelamento/estorno com motivo, data e vínculo ao original, seguindo a ideia já aplicada na cantina.
- **Internação agendada:** a tela só oferece encerramento para internação ativa. Falta um caminho claro para cancelar um agendamento ou corrigir uma data cadastrada incorretamente. Definir o efeito sobre cobranças antes de implementar.
- **Consulta de cobranças:** a tela de contas a receber identifica a internação pelo número, enquanto mensalidades já apresenta o nome do residente. Incluir nome, responsável e busca para facilitar identificação e reduzir lançamento na pessoa errada.
- **Encerramento particular:** as mensalidades futuras permanecem; não classifiquei isso automaticamente como defeito, pois depende do contrato. Mostrar o que continuará devido e permitir o acerto previsto pela regra da clínica.

## Preparação proporcional para atualizações futuras

**Primeira etapa — confiabilidade:** corrigir os problemas de saldo, datas e acerto de convênio; manter testes automatizados com bancos temporários para venda/estorno, descontos, pagamentos parciais e encerramento. O teste manual existente não substitui regressão isolada.

**Segunda etapa — operação diária:** pesquisa e filtros consistentes, extrato por residente, recibos, exportação CSV/Excel, despesas recorrentes e tela de backup com data da última cópia. O campo de recorrência já existe; sua automação deve evitar gerar contas duplicadas.

**Terceira etapa — gestão:** conciliação bancária, identificação de pagamentos por cobrança, contas bancárias/caixas separados, saldo inicial e fechamento mensal. O fluxo atual soma recebimentos e entradas bancárias independentes: uma conciliação futura deve vincular a mesma entrada para não contá-la duas vezes. A relação entre dinheiro das carteiras e caixa da clínica precisa ser definida antes de somar esses movimentos; crédito e consumo não devem virar duas entradas do mesmo dinheiro.

**Evolução técnica gradual:**

- Manter SQLite enquanto o uso for local e pequeno. Padronizar conexões: alguns módulos usam `conectar`, outros abrem SQLite diretamente, sem a mesma configuração de integridade referencial e timeout.
- Padronizar dinheiro em centavos, inclusive na cantina, onde existem valores `REAL` e arredondamentos. Planejar migração com conferência de saldos.
- Criar migrações numeradas e backup antes de mudanças de estrutura. Hoje as alterações de esquema ficam junto de `criar_tabelas`.
- Separar `frontend/js/app.js` por módulo conforme novos recursos forem adicionados; já existe uma boa base de utilitários/componentes extraídos.
- Para mais acessos simultâneos, colocar leitura de saldo e gravação dos recebimentos/pagamentos na mesma transação protegida, e prever prevenção de reenvio duplicado. O servidor usa threads; esse risco foi identificado no código, sem teste de carga nesta análise.
- Reduzir consultas repetidas por conta no dashboard e nas listagens quando houver crescimento. Fazer paginação e consultas agregadas antes de considerar uma mudança de banco.
- Backup externo e teste periódico de restauração: as cópias atuais ficam na mesma máquina. Para acesso em vários computadores, definir claramente instalação principal e cópias de consulta, ou uma API central; a sincronização futura não deve funcionar como edição concorrente do mesmo arquivo SQLite.

## Ordem sugerida

1. Saldo da cantina, validação de recebimentos e acerto de convênio.
2. Encerramento futuro, correção de crédito, relatórios e data local.
3. Histórico de estornos, coerência contratual e testes de regressão.
4. Melhorias de consulta, recibos, recorrência e exportação.
5. Conciliação e acesso por várias instalações quando houver demanda real.

# Análise do sistema — 13/09/2026

Escopo: cadastros, internações, financeiro, cantina, estoque, relatórios, integração entre interface e servidor, desempenho e continuidade operacional. Login e controle de acesso foram excluídos. A análise considera os arquivos atuais do diretório de trabalho, inclusive alterações ainda não commitadas.

Foi feita leitura do código, das migrações e da documentação, execução dos testes disponíveis e reprodução dirigida em banco temporário. Não foi auditado o conteúdo financeiro real da clínica, não foi feita alteração funcional e não houve medição em um computador fraco. As oportunidades de desempenho são fundamentadas no código; os ganhos precisam ser medidos.

## Diagnóstico

O sistema já tem uma base funcional extensa, mas há uma falha bloqueadora na comunicação das gravações do frontend e algumas regras temporais inconsistentes. Antes de ampliar funcionalidades, a prioridade é corrigir a integração e garantir recuperação dos dados. Para computadores modestos, os principais alvos são consultas repetidas, carregamento integral de históricos e escrita no banco durante consultas.

Já estão implementados: valores em centavos; cadastro e vínculo de responsáveis; modalidades particular, social, convênio e voluntário; validação de sobreposição de internações; geração de cobranças; pagamentos parciais, descontos e encargos informados; estornos com histórico; devoluções; prévia de acerto de saída; prorrogação; despesas recorrentes com geração explícita; carteira com saldo negativo; venda por cupom; baixa de estoque e reposição por estorno; preços por vigência; conciliação de entradas; conferência e fechamento versionado; recibos de mensalidade; extratos e impressão; migrações, auditoria e proteção de reenvios no servidor; backup local e provedores de nuvem.

## Problemas e lacunas prioritárias

### P0 — Gravações da interface incompatíveis com o servidor

`frontend/js/core/api.js:1` envia apenas Content-Type no POST. `src/interface/servidor.py:162` exige Idempotency-Key antes de executar as operações de negócio. `src/infraestrutura/operacoes.py:29` recusa a ausência desse valor.

O cliente real foi exercitado com fetch simulado: o cabeçalho não foi enviado. O validador do servidor rejeitou a chave ausente. Portanto, os POSTs de negócio enviados por esse cliente, quando passam pela validação inicial, são recusados antes de gravar. Isso afeta cadastros, recebimentos, vendas, estornos e outros comandos desse caminho. Os testes de backend introduzem a chave manualmente e não detectam a incompatibilidade.

Correção sugerida: uma chave por operação lógica, preservada em tentativas de recuperação; integrar consulta do resultado e cancelamento da tentativa; mostrar ao operador se a operação foi confirmada, não realizada ou precisa de verificação. Não gerar uma chave nova automaticamente depois de uma resposta perdida. Acrescentar teste usando o cliente real contra o servidor em banco descartável.

### P1 — Movimentações futuras alteram saldos atuais

`src/cantina/vendas.py:56` valida o formato da data do crédito, mas não impede futuro; o saldo é incrementado imediatamente. `src/cantina/produtos.py:538` faz o mesmo com ajustes de estoque. Em reprodução temporária, um crédito para daqui a 30 dias alterou a carteira de 10 para 110 centavos; uma entrada futura alterou o estoque de 20 para 22 unidades.

Correção sugerida: movimentos efetivos devem recusar datas futuras. Se agendamento for necessário, criar uma entidade de previsão que não altere o saldo até a efetivação. Aplicar a mesma regra à correção de créditos e definir a política de movimentações retroativas.

### P1 — Backup novo e restauração antiga não formam um fluxo completo

`src/infraestrutura/backup/providers/local.py` gera arquivos `controle_financeiro_*.db` em pasta configurável. `src/infraestrutura/backup_banco.py` lista apenas `clinica_*.db` na pasta fixa `dados/backups`, e restaura somente a partir dessa pasta. Assim, as cópias novas não aparecem no comando legado de listagem e cópias em outra pasta não são restauradas diretamente por ele.

Correção sugerida: unificar catálogo e restauração para os dois formatos, permitir selecionar a cópia configurada e oferecer prévia de data, tamanho e integridade; manter cópia preventiva; exigir exclusividade operacional durante a restauração; testar recuperação completa em ambiente descartável. Acrescentar recuperação de cópias de nuvem quando usada na instalação.

O automático novo vem desligado, depende do processo aberto e não faz retenção. O README ainda descreve backup diário ao iniciar e retenção de 30 cópias, divergindo da implementação atual. Corrigir essa documentação e tornar visível a ausência de uma cópia recente. Não confundir sucesso local com sucesso dos destinos remotos.

## Lista 1 — Melhorias sugeridas para regras de negócio

P1 = alta prioridade operacional; P2 = evolução relevante; P3 = conforme necessidade da clínica. Uma limitação confirmada não significa necessariamente defeito: alguns comportamentos atuais são escolhas explícitas que precisam de decisão de negócio antes de mudar.

| Prioridade | Tema e situação atual | Melhoria sugerida |
|---|---|---|
| P1 | Datas de créditos e estoque podem ser futuras e alterar o presente. | Separar previsão de efetivação; uniformizar validações temporais e regras de retroatividade. |
| P1 | Fechamento preserva fotografia e detecta divergência posterior, mas não impede lançamento retroativo em mês fechado (`financeiro/conferencia.py`). | Definir se o fechamento deve congelar o período. Se sim, exigir reabertura motivada antes de alterações; senão, dar alerta explícito das competências afetadas e manter revisão pendente visível. |
| P1 | A conciliação suporta uma entrada ligada a um conjunto de recebimentos OU créditos, com igualdade exata; não há alocação parcial (`financeiro/conciliacao.py:56`). | Permitir dividir um depósito entre tratamento e carteira, ou associar vários depósitos a um recebimento, mantendo valor alocado, saldo não conciliado e impossibilidade de duplicação. |
| P1 | Conciliação concentra-se em entradas; importações reais estão em scripts específicos. | Criar importação bancária genérica com prévia, validação e prevenção de duplicatas; incluir saídas, tarifas e identificação da conta bancária. |
| P1 | Fluxo de caixa calcula entradas, saídas e resultado; não há modelo completo de contas bancárias, saldos iniciais e transferências internas. | Controlar saldo por conta e caixa físico; registrar transferências sem tratá-las como receita/despesa; demonstrar abertura + entradas − saídas = fechamento. |
| P1 | Carteira negativa é permitida e a saída preserva a dívida; não há fluxo específico de cobrança dessa dívida. | Criar acompanhamento de débitos da cantina, responsável pelo pagamento, vencimento acordado, acordos e quitação por crédito. Manter separação dos valores do tratamento para evitar duplicidade. Limites de consumo podem ser opcionais, preservando a regra atual de permitir negativo. |
| P1 | Acerto particular oferece manter cobrança ou dispensar mensalidades futuras integralmente. | Se previsto na operação, adicionar proporcionalidade, política de acolhimento e multa contratual, com memória de cálculo e política registrada no contrato. O comportamento atual é explícito, não um cálculo proporcional incompleto. |
| P2 | Configuração de juros/multa é consultável, mas a tela apenas exibe parâmetros e os lançamentos recebem encargos manuais. | Criar edição com vigência, cálculo sugerido, base e periodicidade claras; separar juros e multa; manter valor aplicado e justificativa de alteração. Não aplicar novos parâmetros retroativamente sem regra definida. |
| P2 | Há descontos e prorrogação, mas não foi localizado fluxo próprio de renegociação financeira. | Criar acordo que preserve títulos originais, vincule novas parcelas, registre motivo e impeça a soma da dívida antiga com a renegociada. |
| P2 | Programação recorrente exige comando de geração e não permite editar uma programação ativa. | Exibir a próxima geração e períodos ainda não gerados; permitir reajuste com vigência e preservação de contas anteriores. Geração automática deve ser opção explícita. |
| P2 | Recorrência considera qualquer conta da mesma despesa/data como já existente, inclusive cancelada ou de outro valor (`financeiro/recorrencias.py:35`). | Mostrar conflitos de valor/status e permitir decidir se a conta existente atende à programação. Distinguir cancelar um lançamento de dispensar aquela competência. |
| P2 | Despesas têm setor e natureza, mas fornecedor aparece como texto apenas no estoque. | Cadastrar fornecedores, documento da despesa e vencimentos; relacionar compra de estoque à conta a pagar sem registrar saída antes do pagamento; avaliar rateio entre setores. |
| P2 | Lote e validade são informações do movimento; a venda baixa estoque agregado. | Controlar saldo por lote, consumo por validade, alerta de vencimento e destinação de perdas. Se houver produtos fracionados, definir unidades e precisão; atualmente as quantidades são inteiras. |
| P2 | Custo de entrada é opcional; não há apuração estruturada de custo das mercadorias vendidas. | Definir método de custeio e relatórios de margem, perdas e reposição por giro. Não inferir lucro apenas da soma das vendas. |
| P2 | Estorno de venda é por cupom inteiro. | Adicionar devolução parcial por item/quantidade se necessária, distinguindo retorno ao estoque de perda, preservando preço original e saldo da carteira. |
| P2 | Recibo numerado é restrito a recebimentos de mensalidade (`financeiro/recibos.py:23`). | Incluir acolhimento, créditos e devoluções em documentos apropriados, com numeração e dados preservados; guardar o pagador efetivo quando diferente do responsável contratual. |
| P2 | Extratos recalculam saldos pela situação atual; fechamento mensal preserva movimentos, mas não é uma posição histórica completa de todos os direitos e obrigações. | Oferecer posição em uma data e visão atual claramente separadas; manter histórico suficiente de ajustes para reconstruir saldos sem reinterpretar o passado. |
| P2 | Relatórios cobrem operação e fluxo realizado; há alerta de vencimentos, mas não previsão financeira completa. | Incluir projeção de caixa, atraso por faixas, previsto versus realizado, orçamento por setor e relatórios específicos de carteira negativa. Separar competência de vencimento e pagamento. |
| P2 | Documento/comprovante é geralmente texto; relatórios são impressos pela interface. | Vincular anexos, disponibilizar exportação CSV e parametrizar dados institucionais hoje fixos na apresentação. Definir backup dos anexos junto do banco. |
| P3 | Cadastro de residente é enxuto e não há gestão de capacidade/leitos no escopo encontrado. | Se útil à gestão, incluir capacidade, vagas, datas previstas de saída e alertas de término de contrato. Não presumir necessidade de prontuário clínico para completar o financeiro. |

## Lista 2 — Melhorias de desempenho para computadores mais fracos

| Ordem | Evidência no código | Mudança sugerida e benefício esperado |
|---|---|---|
| 1 | Listagens sem paginação em consultas, contas, conciliação e relatórios; tabelas criam todas as linhas. | Filtrar e paginar no servidor, começando com 50–100 registros; retornar totais separados. Reduzir JSON, memória e quantidade de elementos da tela. Não calcular total geral pela página atual. |
| 2 | `_dashboard`, em `interface/servidor.py:89`, lista todas as contas e chama `calcular_total_pago` para cada uma, apesar de `listar_contas` já devolver o restante. Também lê todos os movimentos para exibir dez. | Reutilizar totais já calculados e buscar os dez últimos diretamente. Depois consolidar indicadores com consultas agregadas. Evitar crescimento de consultas proporcional ao número de contas. |
| 3 | `financeiro/caixa.py:195` monta movimentos para somar; `/api/caixa` e relatório financeiro chamam novamente a listagem. | Produzir resumo e detalhes a partir da mesma leitura consistente; usar SUM/GROUP BY quando apenas totais forem necessários, preservando as regras de conciliação e devolução. |
| 4 | `cantina/api_publica.py:14` carrega todos os movimentos e percorre o histórico inteiro novamente para cada carteira. | Agrupar por carteira em uma passagem ou em SQL, levando o custo de carteiras × movimentos para próximo de carteiras + movimentos. Filtrar o período no banco quando possível. |
| 5 | `cadastros/internacoes.py:11` atualiza cada internação, zera todos os residentes e reativa os vigentes; é chamado em listagens e detalhes. | Calcular atividade na leitura ou sincronizar apenas quando necessário, alterando só registros cujo estado mudou. Tratar a mudança de dia com a aplicação aberta. Reduzir escrita e disputa pelo disco durante consultas. |
| 6 | Há índices únicos de integridade, mas faltam índices explícitos para várias relações e datas usadas nos filtros/somas. | Examinar EXPLAIN QUERY PLAN e testar índices em recebimentos(cobranca_id), pagamentos_saida(conta_pagar_id), movimentacoes_carteira(carteira_id,data_movimentacao), movimentacoes_estoque(item_id,data_movimentacao), internacoes(residente_id) e itens_cantina_valores(item_id,data_inicio_valor). Considerar status/vencimento conforme consultas reais; não duplicar índices já cobertos. |
| 7 | `components/filters.js:20` visita todas as linhas a cada digitação e normaliza textos repetidamente. | Usar pequena espera de 150–250 ms após digitação, preparar texto normalizado uma vez e migrar busca de grandes conjuntos para o servidor. |
| 8 | `app.js:476` desmonta/recria painéis e recarrega dados; formulários buscam listas inteiras para localizar um ID. | Usar endpoints de detalhe, atualizar apenas a área afetada e preservar filtro/página/seleção. Reaproveitar cadastros com invalidação após edição; não usar cache financeiro sem atualização confiável. |
| 9 | O cliente não tem cancelamento de leituras; navegar rapidamente pode deixar consultas trabalhando sem utilidade. | Cancelar GETs abandonados e descartar respostas obsoletas. Para POSTs, consultar resultado pela chave da operação: cancelar a espera não desfaz a gravação. |
| 10 | Arquivos estáticos recebem Cache-Control: no-store (`interface/servidor.py:423`); módulos são importados antecipadamente. | Versionar arquivos e usar revalidação/cache apropriado de CSS/JS; carregar painéis opcionais quando abertos. Manter dados operacionais atualizados. Prioridade menor que consultas e paginação. |
| 11 | `infraestrutura/banco.py:10` não define WAL; existe servidor com threads e operações de escrita durante consultas. | Após reduzir escritas desnecessárias, comparar modos de journal com carga real. Avaliar WAL em disco local com testes de backup, restauração e concorrência. Não reduzir garantias de durabilidade para ganhar velocidade. |
| 12 | `iniciar.ps1` importa SDKs de nuvem para verificar dependências em toda abertura. Backup pode iniciar logo após abrir a aplicação. | Separar preparação/instalação de execução, reduzir verificações repetidas e escalonar trabalho de backup sem atrasar excessivamente uma cópia necessária. Medir tempo até a primeira tela utilizável. |
| 13 | Conferências e fechamentos retornam históricos completos com fotografias JSON; backups não têm retenção. | Paginar histórico e abrir fotografias sob demanda; monitorar tamanho do banco e espaço livre; configurar retenção explícita de backups. Preservar histórico financeiro e a proteção de reenvio; não apagar registros indiscriminadamente. |
| 14 | Relatórios imprimem todo o conteúdo em uma única montagem de HTML. | Exigir período em relatórios volumosos, exportar dados sem criar milhares de elementos e carregar prévias limitadas. Garantir que a exportação completa não seja confundida com a página visível. |
| 15 | Logs existentes registram falhas e requisições, mas não fornecem medição sistemática de latência/consultas. | Registrar duração das rotas, volume de resposta e consultas lentas sem dados pessoais; criar massa sintética para comparar desempenho antes e depois. |

Não foi encontrada evidência que justifique substituir SQLite, JavaScript puro ou WebView2 como primeira medida. A arquitetura pode ser mantida enquanto se reduz o trabalho desnecessário.

## Validação e limitações

- Python: 89 testes executados no runtime disponível; 87 aprovados e 2 com erro por ausência de `google.auth` e `botocore` no ambiente de teste. Os dois erros foram nos testes de provedores de backup, não uma falha funcional comprovada desses provedores.
- JavaScript: os sete scripts de `tests/*.mjs` concluíram com sucesso. Eles validam partes da lógica e composição, mas não demonstram o fluxo completo de gravação da interface.
- Reprodução dirigida, banco descartável: crédito futuro e entrada futura de estoque aceitos e refletidos imediatamente no saldo.
- Reprodução dirigida do cliente: POST sem Idempotency-Key confirmado por captura do fetch; chave ausente rejeitada pelo validador do servidor.
- Não foram feitas chamadas reais a R2/Drive, restauração do banco de produção, testes visuais manuais ou benchmark em equipamento fraco.
- O Python da `.venv` não pôde ser iniciado neste ambiente; os testes usaram o runtime Python disponibilizado pela ferramenta de dependências.

## Sequência recomendada e critérios de conclusão

1. Corrigir integração de gravações e testar cadastro → internação → recebimento → venda → estorno usando frontend e servidor reais com banco temporário; testar clique repetido e resposta perdida.
2. Corrigir datas futuras e unificar recuperação de backups; demonstrar restauração completa de uma cópia criada pelo módulo novo.
3. Otimizar dashboard, consultas de caixa, conferência de carteiras e sincronização de residentes; implantar paginação e índices medidos.
4. Definir política de período fechado, alocações bancárias, acerto e cobrança de carteiras; implementar sem alterar silenciosamente contratos existentes.
5. Expandir fornecedores, compras, documentos, relatórios e estoque por lote conforme frequência real de uso.

Para desempenho, usar massa sintética em três escalas (por exemplo, 1 mil, 10 mil e 100 mil movimentos) e medir início, dashboard, busca, venda, relatório e backup no equipamento-alvo. Como metas iniciais a validar, buscar telas comuns em até 1–2 segundos e busca paginada em até 300 ms, além de estabilidade de memória ao repetir a navegação. Esses números são critérios propostos, não resultados medidos nem promessa para qualquer computador.

# Desempenho e benchmark

Este documento registra o procedimento introduzido em 15/09/2026. O relatório original em
`docs/ANALISE_SISTEMA_2026-09-13.md` permanece como histórico.

## Melhorias medidas

- O dashboard usa o saldo já consolidado pela consulta de contas a pagar e deixou de abrir uma
  consulta adicional para cada conta.
- Os totais do caixa são calculados com `SUM` no SQLite. Quando a tela também pede os movimentos,
  resumo e detalhes usam a mesma conexão e a mesma leitura lógica.
- A conferência de carteiras calcula residual, abertura e fechamento por agrupamento SQL, sem
  percorrer todo o histórico novamente para cada carteira.
- A sincronização de internações e residentes grava apenas estados que mudaram. A verificação na
  abertura continua tratando a mudança de dia com o programa aberto.
- Consultas simultâneas idênticas do cliente compartilham a resposta. A busca local espera 200 ms
  e reutiliza o texto normalizado das linhas.
- CSS, JavaScript, fontes e imagens usam revalidação por ETag. O HTML continua revalidado a cada
  abertura para evitar misturar versões.
- A migração financeira 10 cria índices para vínculos, datas e ordenações usados nas consultas.

## Como reproduzir

O comando abaixo cria e remove bancos temporários. Ele não abre `dados/clinica.db`:

```powershell
python -m src.scripts.benchmark_desempenho --volumes 1000 10000
python -m src.scripts.benchmark_desempenho --volumes 100000 --somente-atual
```

Cada cenário é executado cinco vezes. `frio_ms` é a primeira execução e
`mediana_quente_ms` é a mediana das demais. A massa distribui pagamentos e movimentos entre meses,
carteiras, créditos, compras e estornos. O benchmark compara especificamente os algoritmos removidos
com os agregados substitutos; ele não representa o tempo total de abertura da interface.

## Resultado neste ambiente

Runtime: Python 3.14, Windows, disco local. Os tempos estão em milissegundos.

| Registros | Consulta | Antes, mediana | Depois, mediana | Resultado financeiro igual |
|---:|---|---:|---:|:---:|
| 1.000 | Contas do dashboard | 73,183 | 0,672 | Sim |
| 1.000 | Conferência de carteiras | 4,012 | 0,173 | Sim |
| 10.000 | Contas do dashboard | 3.366,354 | 5,246 | Sim |
| 10.000 | Conferência de carteiras | 168,084 | 0,752 | Sim |
| 100.000 | Contas do dashboard | não concluído em limite seguro | 71,912 | verificado pelo total sintético |
| 100.000 | Conferência de carteiras | não concluído em limite seguro | 9,090 | verificado pelo total sintético |

A execução conjunta do algoritmo antigo com 100 mil registros foi interrompida após ultrapassar um
minuto. Por isso não há número “antes” inventado nessa escala.

## Pontos ainda dependentes do computador-alvo

Não houve acesso a uma máquina fraca nem medição confiável do WebView2, memória residente, tempo até
a primeira tela, backup durante venda ou armazenamento em rede. Paginação completa das listagens e
prévia limitada de relatórios continuam sendo etapas próprias: exigem atualizar cada tela e suas
exportações sem mudar os totais nem truncar dados silenciosamente.

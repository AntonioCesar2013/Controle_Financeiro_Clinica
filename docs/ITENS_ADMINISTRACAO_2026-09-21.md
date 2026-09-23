# Itens administrativos

O módulo mantém inventário administrativo separado da Cantina e dos pertences de residentes. A migração `administracao:1` cria `itens_administracao` e `movimentacoes_itens_administracao` quando a aplicação inicializa uma versão atualizada. Ela foi validada somente em bancos temporários; nenhum banco real foi aberto ou migrado durante o desenvolvimento.

## Modelo e operações

- Patrimônio informado identifica uma unidade e permanece único mesmo após baixa.
- Lotes sem patrimônio usam quantidades inteiras e podem chegar a saldo zero.
- O valor de aquisição é o total histórico inicial e não é recalculado por movimentos.
- Cadastro, entrada, saída, ajuste para saldo alvo, transferência integral, baixa, edição, inativação e reativação geram histórico imutável.
- Transferências guardam nomes e localizações anteriores e novas. A ordem do histórico é a ordem de registro; a data efetiva também é exibida.
- Toda mutação usa `versao_esperada`. Conflitos exigem recarregar o item.
- Setor inativo bloqueia aumento e reativação, mas permite reduzir saldo ou transferir para setor ativo.
- Baixa total inativa; saída comum até zero mantém o item ativo; inativação manual exige saldo zero.

## API

Consultas: `GET /api/administracao/itens`, `/detalhe` e `/historico`.

Gravações: `POST /api/administracao/itens`, `/editar`, `/movimentar`, `/transferir` e `/status`. As gravações usam o pipeline existente de `Idempotency-Key` e a mesma transação do histórico.

## Interface

Abra **Administração → Itens administrativos**. A tabela usa seleção de linha e barra de ações, sem coluna de ações. Os indicadores respeitam o filtro completo e apresentam quantidades separadas por unidade. O botão **Novo item** permanece disponível; as demais ações dependem da seleção e da elegibilidade do registro.

Não há integração automática com contas a pagar, caixa, depreciação, Cantina ou pertences pessoais. Transferência parcial e distribuição em vários locais permanecem fora do escopo desta versão.

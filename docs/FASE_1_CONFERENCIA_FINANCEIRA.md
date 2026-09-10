# Fase 1 — Conferência financeira

Acesse **Financeiro → Conferência financeira**. As três abas atendem à
conciliação das entradas, à conferência dos saldos atuais e ao fechamento dos
movimentos de cada mês. As carteiras permanecem separadas das receitas da
clínica, conforme a regra confirmada para esta instalação.

## 1. Conciliação bancária

1. Localize a entrada importada pelo valor, data, descrição e documento.
2. Clique em **Conciliar** e escolha o destino:
   - **Recebimentos da clínica:** marque os recebimentos já registrados.
   - **Créditos das carteiras:** marque os créditos já registrados.
   - **Outra receita da clínica:** identifique a origem de uma entrada que não
     corresponda a cobrança ou carteira, por exemplo uma doação.
3. Informe o documento ou motivo que comprova o vínculo e confirme.

Uma entrada pode corresponder a vários lançamentos do mesmo destino, desde
que a soma seja exatamente igual ao valor bancário. Cada lançamento só pode
pertencer a uma conciliação ativa. O vínculo não cria recebimentos ou créditos;
se estiverem faltando, registre-os nas telas habituais e volte à conferência.
Não é feito casamento automático por valor ou por nome.

Para recebimentos conciliados, o caixa conta somente a entrada bancária, na
data do banco. O recebimento original continua na cobrança, extrato e recibo.
Assim, se a compensação ocorrer no mês seguinte, o caixa e o histórico do
recebimento podem ter datas diferentes. Confirme essa diferença no documento.

Entradas vinculadas a créditos de carteira deixam de compor o caixa da clínica.
Os créditos e as compras continuam na movimentação da carteira, por suas datas
originais. Compras e saldos das carteiras não são receitas adicionais no caixa.

Entradas ainda pendentes permanecem no cálculo legado do caixa, identificadas
com **[Conciliação pendente]**. Esses totais são provisórios: podem incluir um
recebimento ainda não vinculado ou um depósito de carteira. O fechamento do mês
é bloqueado enquanto houver entradas bancárias pendentes nesse mês.

Para corrigir ou estornar um lançamento conciliado, use **Ver / desfazer**,
informe o motivo, corrija o lançamento e faça a nova conciliação. O histórico
preserva os dados do vínculo original. Ao desfazer, a entrada volta a ficar
pendente; até a nova conciliação, os valores voltam ao cálculo separado.

Nesta etapa não há rateio parcial de um lançamento entre entradas nem mistura
de recebimentos e carteiras na mesma entrada. Casos desse tipo devem ser
conferidos antes do fechamento; não classifique como outra receita apenas
para eliminar uma pendência.

## 2. Conferência de saldos de início de operação

1. Abra **Conferência de saldos** na data em que fará a conferência.
2. Compare cada conta a receber e a pagar com os controles externos. A posição
   inclui contas futuras em aberto; contas canceladas não entram.
3. Compare cada carteira, inclusive inativas e negativas, com o controle do
   residente. Conte fisicamente cada produto de estoque, na unidade indicada.
   Serviços não entram na contagem física.
4. Digite os valores efetivamente conferidos, inclusive zeros, seu nome e os
   documentos utilizados.
5. Registre a comparação. Todos os itens devem ser preenchidos.

O registro será **CONFERIDA** quando todos os valores coincidirem ou
**DIVERGENTE** quando houver diferenças. As diferenças ficam detalhadas no
histórico. A conferência não sobrescreve contas, carteiras ou estoque.
Corrija os lançamentos pelas rotinas correspondentes e registre nova conferência.
Se houver movimentação que altere a posição enquanto a tela estiver aberta,
o registro será recusado até a atualização e nova conferência.

Esta é uma fotografia dos saldos atuais, não uma reconstrução histórica de
contas a receber, contas a pagar ou estoque. Registros antigos de carteiras sem
movimentação de abertura são tratados como saldo anterior ao histórico;
por isso é indispensável conferir os valores com os documentos externos.

## 3. Fechamento mensal

1. Escolha um mês já encerrado.
2. Resolva as entradas bancárias pendentes.
3. Confira os movimentos e digite os cinco totais dos documentos: entradas e
   saídas da clínica, créditos e compras das carteiras e saldo final das carteiras.
4. Informe quem conferiu e quais documentos foram usados.
5. Registre o fechamento. Totais divergentes ou uma tela desatualizada impedem
   a conclusão.

Cada revisão guarda os movimentos, totais, identificação da conferência e data
do registro. A consulta mostra **FECHADO** enquanto os dados atuais coincidirem
com a revisão registrada. Alterações retroativas que afetem os dados guardados
fazem a situação mudar para **REVISAR** quando o mês for consultado.

Os ajustes posteriores continuam permitidos. Use **Reabrir mês com justificativa**,
registre o motivo, confira os dados corrigidos e feche novamente. Isso cria
outra revisão sem substituir os números da anterior. Não há bloqueio global
de edição por competência nesta fase, nem notificação em segundo plano.

O fechamento mensal cobre movimentos de caixa e carteiras. A conferência das
posições de contas e estoque é feita separadamente, na segunda aba.

## Validação para iniciar a operação real

A implementação e os testes não atestam os dados reais da clínica. Para
concluir a conferência operacional, é necessário comparar com os extratos,
contratos, controles das carteiras e inventário físico, obter uma conferência
sem divergências e fechar um mês sem pendências. Nenhum valor real foi
conciliado ou confirmado automaticamente durante o desenvolvimento.

## Testes

- `python -m unittest discover -s tests -v`
- `node tests/conferencia.mjs`
- `node tests/datas.mjs`
- `node tests/documentos.mjs`
- `node tests/modulos_frontend.mjs`

Os testes usam bancos temporários. A migração `financeiro:3` cria as tabelas,
índices e proteções na inicialização normal, preservando os lançamentos antigos.

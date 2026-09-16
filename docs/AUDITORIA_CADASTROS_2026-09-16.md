# Auditoria do módulo de cadastros — 16/09/2026

Escopo: residentes, responsáveis, colaboradores, convênios, internações, contato principal, formulários e integração com a API. Revisão do código e testes em bancos temporários. Nenhuma correção funcional aplicada e nenhum dado real utilizado. A interface foi inspecionada pelo código; não houve teste manual completo em navegador/WebView.

## Erros encontrados

### 1. P1 — Cadastro de voluntário bloqueado pelo período oculto

- Referências: `frontend/js/app.js:632`, `:637`, `:1153`; `src/interface/validacao.py:19`.
- Reprodução: abrir Nova internação, selecionar Voluntário sem preencher antes o período, informar os serviços e salvar.
- O formulário oculta o período e remove sua obrigatoriedade, mas envia `periodo_tratamento: ""`. A validação da API exige o campo para todas as modalidades.
- Resultado reproduzido no pipeline POST: `Preencha o campo obrigatório: periodo_tratamento.` O domínio já trata voluntário com período zero.
- Correção: tornar a validação condicional à modalidade e normalizar a ausência de período no voluntário; manter período positivo para as demais modalidades. Verificar também a troca de modalidade com campos ocultos ainda preenchidos/inválidos.

### 2. P1 — Troca de responsável contratual seleciona outra pessoa por padrão

- Referências: `frontend/js/app.js:738`, `:848`.
- Evidência por inspeção: o formulário consulta somente a lista de responsáveis ativos e usa `selectOptions(guardians)`, sem carregar o `responsavel_id` da internação e sem marcar a opção atual.
- Reprodução na interface: cadastrar dois responsáveis, vincular a internação ao segundo na ordem alfabética, abrir Responsável e salvar sem alterar o campo.
- Resultado previsto pelo código: o primeiro responsável da lista é enviado e substitui o contratual atual. O título “Alterar responsável principal” ainda confunde esse vínculo com o contato principal independente.
- Correção: selecionar explicitamente o responsável contratual atual; se estiver inativo, exibi-lo como atual, sem substituição automática, e exigir escolha explícita para trocar. Identificar o campo como responsável contratual. Não oferecer a ação como disponível em contratos encerrados/cancelados, pois o backend a recusa.

### 3. P2 — Cadastro duplicado informa sucesso e descarta os dados digitados

- Referências: `src/cadastros/residentes.py:26`; `src/cadastros/responsaveis.py:29`; `frontend/js/app.js:929`, `:1134`.
- Reprodução: cadastrar uma pessoa e tentar novo cadastro com o mesmo documento, nome e telefone/cidade diferentes.
- Resultado reproduzido: backend retorna `sucesso: true, existe: true` com os dados antigos; os formulários ignoram a resposta e anunciam que o cadastro foi salvo. Não há duplicação, mas o usuário recebe confirmação de dados que não foram gravados.
- Correção: tratar `existe` explicitamente no frontend, informar o cadastro existente e permitir acesso à edição; preservar os dados existentes e não confirmar uma criação/alteração que não ocorreu.

### 4. P2 — Documentos pendentes aceitos na criação impedem edição posterior

- Referências: `src/cadastros/residentes.py:7`, `:92`; `src/cadastros/responsaveis.py:7`, `:99`; `frontend/js/app.js:843`, `:847`, `:519`; `frontend/js/utils/masks.js`.
- Reprodução: criar por domínio/API um residente ou responsável com `PENDENTE-TESTE`; editar somente nome/cidade/telefone mantendo o identificador.
- Resultado reproduzido: a edição remove os caracteres não numéricos e recusa o documento. Na interface, a aplicação automática de máscaras também remove o identificador pendente ao abrir o formulário.
- Correção: preservar identificadores pendentes já existentes na edição de outros campos, permitir regularização para documento normal e apresentar o estado pendente sem passar pela máscara numérica. Não liberar arbitrariamente novos documentos inválidos.

### 5. P2 — Divergência sobre o dia de encerramento bloqueia reinternação

- Referências: `src/cadastros/vigencia.py:15`; `src/cadastros/internacoes.py:30`, `:162`, `:170`, `:416`.
- Reprodução em banco temporário: criar internação social, encerrá-la e tentar nova internação do mesmo residente na mesma data.
- Resultado reproduzido: a consulta de vigência retorna falso no dia da saída e o residente fica inativo, mas o cadastro recusa a nova internação por período coincidente. A prorrogação também compara o encerramento antecipado como limite inclusivo.
- Correção: centralizar a convenção de limites, respeitando a regra explicitada em `vigencia.py` de que a saída antecipada encerra a vigência naquele dia. Preservar a regra específica de cobrança de diárias e testar os limites sem alterar valores financeiros incidentalmente.

### 6. P2 — API aceita booleanos textuais na validação e os rejeita na gravação

- Referências: `src/interface/validacao.py:98`; `src/cadastros/responsaveis.py:105`; `src/cadastros/convenios.py:10`.
- Reprodução pelo pipeline POST: editar responsável com `ativo: "false"`; cadastrar convênio com `ativo: "true"`.
- Resultado reproduzido: a validação estrutural aceita ambos, mas o domínio usa `int()` e rejeita. No convênio, a mensagem ainda aponta incorretamente um problema no valor da diária.
- Impacto: contrato inconsistente para consumidores da API; os formulários atuais que enviam `"0"`/`"1"` não são afetados por esse caso específico.
- Correção: normalizar as representações admitidas para 0/1 em um ponto comum e testar booleanos JSON, strings admitidas e entradas inválidas.

### 7. P3 — Nova internação oferece responsáveis inativos como opções válidas

- Referências: `frontend/js/app.js:621`, `:629`; `src/interface/consultas_interface.py:26`; `src/cadastros/internacoes.py:126`.
- Evidência por inspeção: GET lista todos os responsáveis; Nova internação monta opções sem filtrar `ativo`. A alteração de responsável já faz esse filtro.
- Reprodução na interface: inativar um responsável e abrir Nova internação. Ele aparece normalmente e pode ser a seleção inicial. Se todos estiverem inativos, o aviso de cadastro necessário não aparece porque apenas o tamanho da lista é verificado.
- Impacto: o usuário preenche o formulário e só ao salvar recebe a recusa do backend. Não houve evidência de gravação com responsável inativo; a proteção do domínio funciona.
- Correção: oferecer somente ativos e orientar cadastrar/reativar um responsável quando não houver elegíveis.

## Validação realizada

- `python -m unittest discover -s tests -p 'test_fluxos*.py'`: 32 testes aprovados.
- `python -m unittest discover -s tests -p test_regressoes.py`: 24 testes aprovados. Total das duas execuções Python: 56 testes, todos aprovados.
- `node tests/workflows.mjs`, `node tests/modulos_frontend.mjs`, `node tests/interface_visual.mjs`, `node tests/datas.mjs`: todos concluídos com sucesso. São verificações automatizadas de lógica/estrutura, não um teste visual real de navegador.
- `python docs/reproduzir_auditoria_cadastros_2026_09_16.py`: reproduziu e confirmou os achados 1, 3, 4, 5 e 6, incluindo ambas as entidades nos casos 3 e 4. Os achados 2 e 7 decorrem da inspeção do fluxo frontend.
- O script de reprodução confirma o comportamento defeituoso atual; após a correção, suas asserções devem ser substituídas por regressões que exijam o comportamento correto.
- O Python da `.venv` falhou ao iniciar com “Acesso negado”; os testes foram executados com o Python do runtime disponibilizado pelo aplicativo. Isso é uma limitação do ambiente de teste, não um erro atribuído ao módulo.

Não foram encontrados defeitos adicionais confirmados no fluxo básico de colaboradores nesta revisão. Isso não significa cobertura exaustiva. O controle de acesso desativado está documentado como intencional nesta fase e não foi classificado como regressão de cadastro. A revisão não estabelece uma nova política de validação de dígitos verificadores de CPF/CNPJ.

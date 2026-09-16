# Prompt para correção — Codex 5.1

Trabalhe no projeto `C:\Projetos\Controle_Financeiro_Clinica` e corrija os erros do módulo de cadastros documentados em `docs/AUDITORIA_CADASTROS_2026-09-16.md`.

Leia primeiro as instruções AGENTS.md aplicáveis, o relatório e `docs/reproduzir_auditoria_cadastros_2026_09_16.py`. Confira o estado do Git e preserve alterações preexistentes. O objetivo é implementar e validar as correções, não apenas apresentar um plano.

Restrições:

- Não execute populadores, `src/test.py` ou testes sobre `dados/clinica.db`. Use bancos temporários com patch de `src.infraestrutura.banco.CAMINHO_BANCO`, seguindo as fixtures existentes.
- Não altere dados reais, não reinicialize bancos, não faça migração destrutiva, commit, push ou publicação.
- Preserve a arquitetura modular, contratos monetários em centavos, atomicidade, idempotência, histórico financeiro e a separação entre contato principal e responsável contratual.
- Não reative autenticação/permissões nem adicione validação obrigatória de dígitos verificadores de documentos como parte desta correção; isso extrapola os achados e pode invalidar fixtures e dados legados.
- Reproduza cada achado antes da alteração. Se algum não se confirmar no código atual, apresente a evidência e não aplique uma mudança especulativa.

Implemente:

1. **Internação voluntária:** corrigir a divergência entre formulário e validação da API. Voluntário com período ausente/vazio deve normalizar para zero e poder ser salvo com serviços preenchidos, sem cobranças. Particular, social e convênio devem continuar exigindo período positivo. Campos ocultos de outra modalidade não devem impedir a submissão nem carregar valores indevidos. Testar mudanças de modalidade e envio realista do formulário.
2. **Responsável contratual:** ao abrir a edição, carregar a internação e selecionar o responsável atual. Salvar sem alterações não deve trocar o vínculo. Se o atual estiver inativo, mostrar a situação e exigir escolha explícita antes de substituí-lo, sem escolher outra pessoa automaticamente. Corrigir o título para responsável contratual e alinhar a disponibilidade da ação aos estados aceitos pelo backend. Não modificar o contato principal ao trocar o contratual.
3. **Documento duplicado:** tratar `existe: true` nos cadastros de residentes/responsáveis. Informar claramente que o documento já pertence a um registro e oferecer acesso à edição. Não mostrar mensagem de criação concluída nem sobrescrever o registro silenciosamente. Preservar compatibilidade de consumidores que reutilizam o retorno existente.
4. **Documento pendente:** permitir editar outros dados mantendo o identificador pendente já persistido e permitir sua substituição por documento normal sem criar outra pessoa. Evitar que máscaras numéricas destruam o identificador ao abrir/salvar o formulário. Não permitir a fabricação arbitrária de novos identificadores pendentes pela edição. Manter unicidade e validações de documentos normais.
5. **Limites da internação:** harmonizar cadastro, prorrogação e consulta de vigência quanto à saída antecipada. Usar a convenção já explicitada em `vigencia.py`: no dia de encerramento antecipado o contrato anterior não está mais vigente. Permitir a reinternação nesse dia sem liberar sobreposições reais. Manter o comportamento do término natural e as regras financeiras de diárias; testar datas anterior, igual e posterior ao encerramento e internações voluntárias/contratos agendados.
6. **Booleanos da API:** normalizar de forma consistente booleanos JSON, `0`, `1`, `"0"`, `"1"`, `"true"`, `"false"` conforme o contrato atual. Garantir que responsável e convênio persistam 0/1; entradas inválidas devem falhar com mensagem do campo correto e nenhuma gravação. Não usar `bool("false")`.
7. **Responsáveis elegíveis:** Nova internação deve listar somente responsáveis ativos. Se não houver nenhum, exibir orientação para cadastrar/reativar, sem permitir envio inválido. Manter a checagem do backend para alterações concorrentes.

Testes e critérios de aceite:

- Criar testes de regressão backend/API em banco descartável e testes de comportamento frontend cobrindo os sete achados. Testes que somente procuram trechos de texto no código não bastam para seleção atual, resposta duplicada e submissão do voluntário.
- O POST de voluntário com payload do formulário deve funcionar; demais modalidades sem período devem falhar sem efeitos parciais.
- Abrir/salvar o responsável contratual sem editar deve preservar o ID atual e o contato principal; testar também atual inativo e ausência de ativos.
- Documento repetido deve ser comunicado sem falsa confirmação; nome/telefone/cidade antigos devem permanecer intactos até edição explícita.
- Nome/cidade/telefone de registros pendentes devem ser editáveis sem perda do identificador; regularização e conflito de unicidade devem ter cobertura.
- Internações adjacentes à saída antecipada devem obedecer à mesma convenção no cadastro, na prorrogação e na vigência. Verificar que as cobranças existentes não mudaram indevidamente.
- Executar os testes existentes pertinentes: `python -m unittest discover -s tests -p 'test_fluxos*.py'`, `python -m unittest discover -s tests -p test_regressoes.py`, testes novos, e `node tests/workflows.mjs`, `node tests/modulos_frontend.mjs`, `node tests/interface_visual.mjs`, `node tests/datas.mjs`. Se modificar contratos da API, executar também os testes de operações/API pertinentes.
- Se o Python da `.venv` estiver indisponível, localizar outro interpretador funcional sem reinstalar ou alterar a configuração do projeto desnecessariamente.
- Revisar o diff final. Entregar lista de correções, arquivos modificados, comandos/resultados dos testes e limitações restantes. Não afirmar teste manual em navegador caso apenas testes automatizados tenham sido executados.

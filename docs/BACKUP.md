# Backup SQLite

## Configuração desta instalação — 22/09/2026

O backup funciona no acesso local sem consultar login, sessão ou perfil de usuário.
A pasta configurada é `C:\Users\Cliente\Documents\backupsistema`, com execução
automática habilitada a cada seis horas enquanto o sistema estiver aberto.
Foi gerada a cópia `controle_financeiro_2026-09-22_084013_033521.db` e testada sua
restauração em banco temporário: integridade aprovada, nenhuma violação de chave
estrangeira e arquivo restaurado idêntico à cópia. O banco operacional não foi
substituído. Acesso e operações sem login foram verificados em 18 testes Python
de backup e no teste JavaScript de status, todos aprovados.

Esta configuração é local ao usuário Windows atual. Uma pasta no próprio computador
não substitui uma cópia externa para recuperação em caso de perda do equipamento.

Em **Administração → Configurações → Backup do sistema**, informe uma pasta absoluta,
salve e use **Executar backup agora**. O seletor abre uma pasta do computador que
executa o WebView2; no navegador, digite o caminho. Pastas inexistentes são criadas
na primeira execução. A pasta precisa permitir gravação e ter espaço disponível.

## Armazenamento e segurança

- Configurações não sensíveis → `%LOCALAPPDATA%\Controle_Financeiro_Clinica\config\backup.json`.
  Caminho calculado por `platformdirs.user_data_path`, sem diretório do fabricante.
- Estado operacional → `backup-status.json` na mesma pasta. Guarda a última tentativa,
  último snapshot local íntegro, destinos, erros sanitizados, nome, tamanho, duração
  e execução ignorada. Não é um histórico financeiro.
- Segredos → **Windows Credential Manager**, serviço `Controle_Financeiro_Clinica.Backup`:
  `r2_access_key_id`, `r2_secret_access_key`, `drive_client_secret`, `drive_token`.
  O último contém o material OAuth, incluindo access token, refresh token e expiração.
- Banco financeiro → **não contém configurações ou credenciais do módulo**; nenhuma
  tabela ou migration foi adicionada. As rotas não passam por `operacoes.executar`,
  que registra corpos de comandos no banco financeiro.
- JSON contém apenas versão, ativação, pasta, intervalo, bucket, endpoint, prefixo,
  Client ID público e ID de pasta Drive. Campos desconhecidos são descartados.
  Arquivos ausentes/inválidos usam defaults seguros, com automático desativado.
- O backend Windows é selecionado explicitamente, sem fallback para cofre em texto.
  Segredos digitados transitam uma vez pelo POST local; campos são limpos e nunca
  preenchidos com o valor armazenado. Não há armazenamento no navegador.
- Logs dos SDKs são suprimidos porque podem conter URLs OAuth e headers; mensagens
  de exceções externas nunca são persistidas nem retornadas ao cliente.

## Arquitetura e arquivos criados

| Arquivo (relativo à raiz) | Responsabilidade |
| --- | --- |
| `src/infraestrutura/backup/__init__.py` | Pacote de infraestrutura |
| `src/infraestrutura/backup/config.py` | Whitelist, defaults, validação e JSON atômico |
| `src/infraestrutura/backup/credentials.py` | Abstração do Credential Manager |
| `src/infraestrutura/backup/snapshot.py` | SQLite Backup API, integridade e renomeação atômica |
| `src/infraestrutura/backup/providers/__init__.py` | Pacote de destinos |
| `src/infraestrutura/backup/providers/base.py` | Classificação de erros temporários e backoff |
| `src/infraestrutura/backup/providers/local.py` | Nome único e destino local |
| `src/infraestrutura/backup/providers/r2.py` | S3/R2 e teste de bucket |
| `src/infraestrutura/backup/providers/drive.py` | OAuth, pasta, teste e upload resumível |
| `src/infraestrutura/backup/service.py` | Orquestração, worker, lock e status independente |
| `src/infraestrutura/backup/scheduler.py` | Agendamento durante a execução do sistema |
| `src/infraestrutura/backup/security.py` | Supressão de diagnósticos sensíveis dos SDKs |
| `src/infraestrutura/backup/folder.py` | Seletor nativo WebView2 |
| `src/interface/rotas/backup.py` | Adaptador HTTP e autorização existente |
| `frontend/js/components/backup.js` | Formulário integrado, ações e polling |
| `tests/test_backup.py` | Testes com SQLite temporário, APIs e cofre simulados |
| `docs/BACKUP.md` | Este guia |

Arquivos alterados: `.gitignore` (dependências temporárias de teste), `requirements.txt`
(dependências), `iniciar.ps1` (verifica dependências antes de iniciar), `main.py`
(mensagem de inicialização), `src/interface/servidor.py` (rotas e ciclo de vida),
`src/infraestrutura/backup_banco.py` (reutiliza snapshot seguro e remove exclusão
automática legada), `frontend/js/app.js` (integração em Configurações), `README.md`
(link para este guia).

## Fluxo e agendamento

O snapshot abre o banco existente em modo somente leitura, chama `Connection.backup`
em páginas com limite de cinco minutos, fecha conexões, exige que **todos** os
resultados de `PRAGMA integrity_check` sejam `ok`, sincroniza e renomeia o temporário
na própria pasta de destino. Em seguida, compacta o snapshot íntegro como `.db.gz`,
valida integralmente o stream gzip e publica o arquivo por renomeação atômica.
Cópias incompletas são excluídas; não há cópia direta do arquivo ativo.

Depois da publicação bem-sucedida, são mantidos os **50 backups automáticos mais
recentes** (`controle_financeiro_*.db` ou `.db.gz`) na pasta configurada. Os mais
antigos são removidos. Arquivos com outros nomes, cópias preventivas de restauração
e backups legados não entram nessa limpeza. Se a criação do novo snapshot falhar,
nenhum backup anterior é removido.

Após sucesso local, R2 e Drive recebem o mesmo arquivo, cada qual com seu resultado.
Uma falha R2 não impede o Drive, nem apaga a cópia local. Sem snapshot íntegro, nenhum
upload ocorre. `last_success` significa **snapshot local íntegro**, não sucesso de
todas as nuvens. `last_r2_success` e `last_drive_success` registram separadamente o
último envio bem-sucedido para cada destino. A tela informa desativação, ausência de
cópia concluída, atraso em relação ao intervalo e falhas parciais. O estado geral
somente aparece **em dia** quando cada destino externo habilitado recebeu o snapshot
local atual; caso contrário, aparece **parcial** e identifica os destinos pendentes.

O automático vem desativado, com intervalo padrão de seis horas. Ao habilitar sem
tentativa anterior, executa no próximo ciclo de verificação (até cinco segundos).
Se já existe tentativa anterior, considera o intervalo decorrido. O scheduler roda
somente enquanto o processo do servidor está vivo; não usa Windows Task Scheduler.
Um lock por instância impede backup/teste/OAuth simultâneos. Um ciclo ocupado é
registrado como ignorado e aguarda o próximo intervalo. Use uma instância do sistema
por banco. Ao fechar, o scheduler para; um upload daemon em curso pode ser interrompido,
mas o snapshot local já concluído permanece. Reinício sinaliza execução interrompida.

A trava entre processos do banco é adquirida antes de preparar schema, executar
migrações ou sincronizar estados. Uma segunda instância, inclusive em outra porta,
é recusada sem escrever no banco. Falhas durante a inicialização liberam a trava
antes de devolver o erro, permitindo uma nova tentativa segura.

Uploads/testes/OAuth rodam em thread e retornam HTTP 202; a interface consulta o status.
Erros temporários têm no máximo três tentativas, com esperas de um e dois segundos.
Erros permanentes/autenticação não são repetidos.

## Catálogo e recuperação local

O comando `python -m src.backup_banco listar` reúne as cópias antigas
`clinica_*.db` de `dados/backups` e as novas `controle_financeiro_*.db` ou
`controle_financeiro_*.db.gz` da pasta configurada. A restauração aceita o nome exibido; se houver nomes iguais em pastas
diferentes, informe o caminho completo. Antes de substituir o banco, o comando
descompacta quando necessário, valida a integridade e as tabelas essenciais, cria uma cópia preventiva em
`dados/backups` e prepara a substituição em arquivo temporário.

A restauração é recusada enquanto uma instância do sistema mantém a trava de uso do
banco. Feche todas as janelas e processos do sistema antes de executar o comando.
Essa trava não transforma o cancelamento de uma interface em encerramento do banco.
Recuperação direta de cópias remotas pela interface não faz parte deste fluxo.

## Acesso administrativo local

A instalação atual é destinada a um único administrador e não exige sessão. O código
de autenticação foi preservado, mas suas verificações obrigatórias permanecem
comentadas. As rotas de backup sem sessão só respondem quando o cliente e o servidor
estão no loopback do próprio computador. Os comandos de gravação também validam a
origem HTTP e o tipo JSON. Segredos de R2 e Drive continuam armazenados no Credential
Manager do Windows e não são devolvidos pela API. O servidor desktop deve permanecer
no endereço local padrão.

## Configurar Cloudflare R2

Crie bucket e credenciais S3 com acesso de leitura/gravação ao bucket. Informe bucket,
endpoint HTTPS da conta (`https://<32-caracteres-da-conta>.r2.cloudflarestorage.com`),
prefixo e as duas chaves na tela. Salve e teste. O teste usa `head_bucket`; a política
precisa autorizá-lo. Upload preserva nome sob `prefixo/AAAA/MM/`. O upload atual usa
`PutObject` (arquivo abaixo do limite de 5 GiB); bancos maiores exigirão multipart.
Referência: [Cloudflare boto3](https://developers.cloudflare.com/r2/examples/aws/boto3/).

## Configurar Google Drive

No projeto Google Cloud, ative Drive API, configure consentimento OAuth e crie cliente
do tipo **Desktop app**. Em modo de teste, inclua a conta nos usuários de teste.
Informe Client ID e Client Secret na tela, salve e conecte. O navegador padrão abre
o consentimento; o callback usa porta efêmera no loopback e espera até três minutos.
Tokens são enviados exclusivamente ao cofre; não há `credentials.json`/`token.json`.

O escopo mínimo `drive.file` acessa arquivos/pastas autorizados ao aplicativo. Deixe
o ID vazio para criar `Controle Financeiro Clinica - Backups`; seu ID fica no JSON.
Um ID de pasta arbitrária já existente pode ser inacessível com esse escopo. Use a
pasta criada pelo aplicativo ou autorize a pasta ao app antes de informar seu ID.
O teste valida tipo, lixeira e capacidade de adicionar arquivos. Não cria snapshot,
mas pode criar a pasta padrão se ainda não configurada. Desconectar apaga o token
local; para revogar também no Google, remova o acesso nas configurações da conta.
Se o consentimento expirar/for revogado, reconecte. Mudança de cliente OAuth invalida
o token local. Referência: [OAuth Desktop](https://googleapis.dev/python/google-auth-oauthlib/1.1.0/_modules/google_auth_oauthlib/flow.html).

## Dependências e validação

Instale pelo arquivo único: `python -m pip install -r requirements.txt`.
Novas dependências diretas: platformdirs, keyring, boto3, google-auth,
google-auth-oauthlib, google-api-python-client, google-auth-httplib2 e httplib2.
As duas últimas são usadas explicitamente no transporte Drive com timeout.

Execute `python -m unittest discover -s tests -v`. Os testes não usam credenciais reais
nem enviam dados financeiros. Integrações reais exigem conta/bucket/consentimento;
teste-os na tela depois da configuração. Verifique também o seletor no WebView2
instalado. Backups não recebem criptografia adicional de arquivo nesta etapa;
configure as permissões da pasta/bucket/conta conforme o ambiente da clínica.

Validação desta entrega: suíte completa com 88 testes aprovada; após acrescentar
o teste HTTP de isolamento e PKCE explícito, os 17 testes do módulo passaram.
Sintaxe dos dois arquivos JavaScript e `git diff --check` aprovados. Execução em
Python 3.12 do runtime disponível, com dependências isoladas em `tmp/backup-deps`
(ignorada pelo Git); o launcher instalará as dependências no ambiente normal.
OAuth real, upload real e diálogo nativo não foram exercitados nesta entrega.

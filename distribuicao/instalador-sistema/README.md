# Instalador somente do sistema

`ControleFinanceiroClinica-Setup.exe`, gerado na raiz do projeto, instala apenas o código executável da
aplicação. Ele não contém Python, WebView2, wheels, banco de dados, configurações,
backups, testes, documentação de desenvolvimento nem dados demonstrativos.

O destino é `%LOCALAPPDATA%\ControleFinanceiroClinica`, que permite ao sistema criar
e atualizar `dados\clinica.db` sem exigir privilégios administrativos. Atualizações
substituem todos os arquivos do programa e preservam `dados`,
`configuracao_local.json` e `.venv`. Se o sistema estiver aberto, a atualização é
interrompida com orientação para fechar a janela antes de tentar novamente.

O instalador cria atalhos no Menu Iniciar e na Área de Trabalho. As dependências
devem estar instaladas previamente.

Os atalhos usam `iniciar.vbs` para iniciar sem janela de console. O lançador registra
saída e erros em `dados\logs` dentro da instalação, com arquivos separados por
execução. Em caso de falha, uma mensagem informa onde consultar os registros.
O `iniciar.cmd` permanece compatível e encaminha para o mesmo lançador oculto.

Para gerar novamente:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\gerar-instalador.ps1
```

# Instalador somente do sistema

`ControleFinanceiroClinica-Setup.exe`, gerado na raiz do projeto, instala apenas o código executável da
aplicação. Ele não contém Python, WebView2, wheels, banco de dados, configurações,
backups, testes, documentação de desenvolvimento nem dados demonstrativos.

O destino é `%LOCALAPPDATA%\ControleFinanceiroClinica`, que permite ao sistema criar
e atualizar `dados\clinica.db` sem exigir privilégios administrativos. Atualizações
preservam a pasta `dados` já existente.

O instalador cria atalhos no Menu Iniciar e na Área de Trabalho. As dependências
devem estar instaladas previamente.

Para gerar novamente:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\gerar-instalador.ps1
```

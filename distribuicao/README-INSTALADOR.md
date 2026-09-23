# Dependências para o instalador — Windows x64

Pacote preparado para **Windows 10/11 x64 com Python 3.14**.

## Conteúdo

- `pre-requisitos/python-3.14.7-amd64.exe`: instalador oficial completo do Python.
- `pre-requisitos/MicrosoftEdgeWebView2RuntimeInstallerX64.exe`: instalador oficial
  completo do WebView2 Evergreen x64, apto para instalação sem internet.
- `dependencias-python/`: 43 wheels, incluindo todas as dependências transitivas.
- `requirements-lock-win64-py314.txt`: versões exatas validadas.
- `instalar_dependencias_offline.ps1`: cria a `.venv`, instala somente dos wheels
  locais (`--no-index`) e verifica os imports da aplicação.

O Python, os wheels e o WebView2 permitem instalação totalmente offline. O instalador
final deve detectar primeiro se o WebView2 Runtime já existe e executar o standalone
somente quando ele estiver ausente.

## Verificações realizadas

- Instalação dos 43 wheels em ambiente virtual vazio usando `--no-index`.
- Imports de WebView, backup local, Credential Manager, R2 e Google Drive aprovados.
- Nenhum pacote-fonte (`.tar.gz`/`.zip`) permanece no conjunto; `proxy_tools` foi
  previamente convertido em wheel puro Python.
- Instalador Python com assinatura válida da Python Software Foundation.
- Instalador WebView2 Evergreen Standalone x64 com assinatura válida da Microsoft
  Corporation.

SHA-256 do Python 3.14.7 x64:

`9D9EB2709EF81BF5CD30DB3C2096BDBC4EA10087C22E62F27D356B36F6AE9649`

Esse hash coincide com o publicado na página oficial da versão.

SHA-256 do WebView2 Evergreen Standalone x64 baixado em 23/09/2026:

`AD9B350625E132481BC0953EEE9E032810134DF9FEDBD7BE364C3F4E0E4DBD64`

## Uso pelo instalador

1. Instale o Python 3.14.7 x64 ou use uma instalação 3.14 x64 existente.
2. Execute `instalar_dependencias_offline.ps1`, passando o caminho de `python.exe`.
3. Detecte o WebView2 Runtime. Se ausente, execute o Evergreen Standalone Installer
   x64 incluído com `/silent /install`.
4. Copie o código da aplicação sem o banco demonstrativo.

Exemplo:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  ".\distribuicao\instalar_dependencias_offline.ps1" `
  -PythonExe "C:\Program Files\Python314\python.exe"
```

O instalador oficial do WebView2 documenta a instalação silenciosa como:

```powershell
MicrosoftEdgeWebView2RuntimeInstallerX64.exe /silent /install
```

param(
    [string]$DestinoAplicacao,
    [switch]$SemInterface,
    [switch]$SemAtalhos
)

$ErrorActionPreference = "Stop"

$nomeAplicacao = "Controle Financeiro da Clinica"
$pastaAplicacao = if ($DestinoAplicacao) {
    [IO.Path]::GetFullPath($DestinoAplicacao)
} else {
    Join-Path $env:LOCALAPPDATA "ControleFinanceiroClinica"
}
$arquivoPacote = Join-Path $PSScriptRoot "sistema.zip"
$pastaTemporaria = Join-Path $env:TEMP ("ControleFinanceiroClinica_" + [guid]::NewGuid().ToString("N"))
$pastaRollback = Join-Path $env:TEMP ("ControleFinanceiroClinica_Rollback_" + [guid]::NewGuid().ToString("N"))
$atualizacaoIniciada = $false

try {
    if (-not (Test-Path -LiteralPath $arquivoPacote)) {
        throw "O pacote interno do sistema não foi encontrado."
    }

    New-Item -ItemType Directory -Path $pastaTemporaria -Force | Out-Null
    Expand-Archive -LiteralPath $arquivoPacote -DestinationPath $pastaTemporaria -Force
    foreach ($obrigatorio in @("main.py", "iniciar.cmd", "iniciar.ps1", "frontend", "src")) {
        if (-not (Test-Path -LiteralPath (Join-Path $pastaTemporaria $obrigatorio))) {
            throw "O pacote está incompleto: $obrigatorio não foi encontrado."
        }
    }

    $processosAbertos = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and
        $_.CommandLine.IndexOf($pastaAplicacao, [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
        $_.Name -match '^python(w)?\.exe$'
    }
    if ($processosAbertos) {
        throw "O sistema está aberto. Feche todas as janelas do Controle Financeiro e execute o instalador novamente."
    }

    New-Item -ItemType Directory -Path $pastaAplicacao -Force | Out-Null
    New-Item -ItemType Directory -Path $pastaRollback -Force | Out-Null

    # Substitui integralmente o programa e preserva dados, configuração local e ambiente Python.
    $preservados = @("dados", "configuracao_local.json", ".venv")
    $atualizacaoIniciada = $true
    Get-ChildItem -LiteralPath $pastaAplicacao -Force | Where-Object {
        $preservados -notcontains $_.Name
    } | ForEach-Object {
        Move-Item -LiteralPath $_.FullName -Destination $pastaRollback -Force
    }
    Get-ChildItem -LiteralPath $pastaTemporaria -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $pastaAplicacao -Recurse -Force
    }

    if (-not (Test-Path -LiteralPath (Join-Path $pastaAplicacao "frontend\js\app.js"))) {
        throw "A nova versão não foi copiada corretamente."
    }

    if (-not $SemAtalhos) {
        $menuInicio = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
        $atalho = Join-Path $menuInicio "$nomeAplicacao.lnk"
        $shell = New-Object -ComObject WScript.Shell
        $link = $shell.CreateShortcut($atalho)
        $link.TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
        $link.Arguments = '"' + (Join-Path $pastaAplicacao "iniciar.vbs") + '"'
        $link.WorkingDirectory = $pastaAplicacao
        $link.Description = $nomeAplicacao
        $link.IconLocation = (Join-Path $pastaAplicacao "frontend\assets\logo-clinica.ico") + ",0"
        $link.Save()

        $desktop = [Environment]::GetFolderPath("Desktop")
        if ($desktop) {
            $atalhoDesktop = Join-Path $desktop "$nomeAplicacao.lnk"
            $linkDesktop = $shell.CreateShortcut($atalhoDesktop)
            $linkDesktop.TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
            $linkDesktop.Arguments = '"' + (Join-Path $pastaAplicacao "iniciar.vbs") + '"'
            $linkDesktop.WorkingDirectory = $pastaAplicacao
            $linkDesktop.Description = $nomeAplicacao
            $linkDesktop.IconLocation = (Join-Path $pastaAplicacao "frontend\assets\logo-clinica.ico") + ",0"
            $linkDesktop.Save()
        }
    }

    $mensagemSucesso = "Sistema instalado ou atualizado com sucesso.`n`nLocal: $pastaAplicacao`n`nO banco de dados, a configuração local e o ambiente Python existente foram preservados.`n`nEste instalador não inclui Python, WebView2 ou bibliotecas Python."
    if ($SemInterface) {
        Write-Host $mensagemSucesso
    } else {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show($mensagemSucesso, $nomeAplicacao, "OK", "Information") | Out-Null
    }
}
catch {
    if ($atualizacaoIniciada -and (Test-Path -LiteralPath $pastaRollback)) {
        try {
            Get-ChildItem -LiteralPath $pastaAplicacao -Force | Where-Object {
                @("dados", "configuracao_local.json", ".venv") -notcontains $_.Name
            } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            Get-ChildItem -LiteralPath $pastaRollback -Force | ForEach-Object {
                Move-Item -LiteralPath $_.FullName -Destination $pastaAplicacao -Force
            }
        } catch {}
    }
    $mensagemErro = "Não foi possível instalar o sistema.`n`n$($_.Exception.Message)"
    if ($SemInterface) {
        Write-Error $mensagemErro
    } else {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show($mensagemErro, $nomeAplicacao, "OK", "Error") | Out-Null
    }
    exit 1
}
finally {
    if (Test-Path -LiteralPath $pastaTemporaria) {
        Remove-Item -LiteralPath $pastaTemporaria -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $pastaRollback) {
        Remove-Item -LiteralPath $pastaRollback -Recurse -Force -ErrorAction SilentlyContinue
    }
}

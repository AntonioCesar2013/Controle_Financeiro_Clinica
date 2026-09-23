$ErrorActionPreference = "Stop"

$nomeAplicacao = "Controle Financeiro da Clinica"
$pastaAplicacao = Join-Path $env:LOCALAPPDATA "ControleFinanceiroClinica"
$arquivoPacote = Join-Path $PSScriptRoot "sistema.zip"
$pastaTemporaria = Join-Path $env:TEMP ("ControleFinanceiroClinica_" + [guid]::NewGuid().ToString("N"))

try {
    if (-not (Test-Path -LiteralPath $arquivoPacote)) {
        throw "O pacote interno do sistema não foi encontrado."
    }

    New-Item -ItemType Directory -Path $pastaTemporaria -Force | Out-Null
    Expand-Archive -LiteralPath $arquivoPacote -DestinationPath $pastaTemporaria -Force
    New-Item -ItemType Directory -Path $pastaAplicacao -Force | Out-Null

    # Copia apenas o programa. A pasta dados existente não faz parte do pacote e é preservada.
    Copy-Item -Path (Join-Path $pastaTemporaria "*") -Destination $pastaAplicacao -Recurse -Force

    $menuInicio = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $atalho = Join-Path $menuInicio "$nomeAplicacao.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($atalho)
    $link.TargetPath = Join-Path $pastaAplicacao "iniciar.cmd"
    $link.WorkingDirectory = $pastaAplicacao
    $link.Description = $nomeAplicacao
    $link.Save()

    $desktop = [Environment]::GetFolderPath("Desktop")
    if ($desktop) {
        $atalhoDesktop = Join-Path $desktop "$nomeAplicacao.lnk"
        $linkDesktop = $shell.CreateShortcut($atalhoDesktop)
        $linkDesktop.TargetPath = Join-Path $pastaAplicacao "iniciar.cmd"
        $linkDesktop.WorkingDirectory = $pastaAplicacao
        $linkDesktop.Description = $nomeAplicacao
        $linkDesktop.Save()
    }

    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Sistema instalado com sucesso.`n`nLocal: $pastaAplicacao`n`nEste instalador não inclui Python, WebView2 ou bibliotecas Python.",
        $nomeAplicacao,
        "OK",
        "Information"
    ) | Out-Null
}
catch {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Não foi possível instalar o sistema.`n`n$($_.Exception.Message)",
        $nomeAplicacao,
        "OK",
        "Error"
    ) | Out-Null
    exit 1
}
finally {
    if (Test-Path -LiteralPath $pastaTemporaria) {
        Remove-Item -LiteralPath $pastaTemporaria -Recurse -Force -ErrorAction SilentlyContinue
    }
}


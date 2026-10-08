$ErrorActionPreference = "Stop"

$nomeAplicacao = "Controle Financeiro da Clinica"
$raizPacote = $PSScriptRoot
$pastaAplicacao = Join-Path $env:LOCALAPPDATA "ControleFinanceiroClinica"
$log = Join-Path $raizPacote "instalacao.log"
$pythonInstalador = Join-Path $raizPacote "pre-requisitos\python-3.14.7-amd64.exe"
$webViewInstalador = Join-Path $raizPacote "pre-requisitos\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"
$instalarDependencias = Join-Path $raizPacote "instalar_dependencias_offline.ps1"
$instalarSistema = Join-Path $raizPacote "sistema\instalar-sistema.ps1"
$pythonDestino = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314"
$pythonDestinoExe = Join-Path $pythonDestino "python.exe"

function Registrar([string]$mensagem) {
    $linha = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $mensagem
    Write-Host $mensagem
    Add-Content -LiteralPath $log -Value $linha -Encoding UTF8
}

function Testar-Python314([string]$executavel) {
    if (-not $executavel -or -not (Test-Path -LiteralPath $executavel -PathType Leaf)) { return $false }
    try {
        $plataforma = & $executavel -c "import platform,struct,sys; print('%d.%d|%s|%d' % (sys.version_info.major,sys.version_info.minor,platform.machine(),struct.calcsize('P')*8))" 2>$null
        return $LASTEXITCODE -eq 0 -and $plataforma.Trim() -eq "3.14|AMD64|64"
    } catch { return $false }
}

function Encontrar-Python314 {
    $candidatos = [System.Collections.Generic.List[string]]::new()
    $candidatos.Add($pythonDestinoExe)
    foreach ($chave in @(
        "HKCU:\Software\Python\PythonCore\3.14\InstallPath",
        "HKLM:\Software\Python\PythonCore\3.14\InstallPath",
        "HKLM:\Software\WOW6432Node\Python\PythonCore\3.14\InstallPath"
    )) {
        try {
            $pasta = (Get-Item -LiteralPath $chave -ErrorAction Stop).GetValue("")
            if ($pasta) { $candidatos.Add((Join-Path $pasta "python.exe")) }
        } catch {}
    }
    foreach ($nome in @("python.exe", "python3.exe")) {
        $comando = Get-Command $nome -ErrorAction SilentlyContinue
        if ($comando) { $candidatos.Add($comando.Source) }
    }
    foreach ($candidato in $candidatos | Select-Object -Unique) {
        if (Testar-Python314 $candidato) { return $candidato }
    }
    return $null
}

function Testar-WebView2 {
    $bases = @(
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft\EdgeWebView\Application"),
        (Join-Path $env:ProgramFiles "Microsoft\EdgeWebView\Application"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\EdgeWebView\Application")
    ) | Where-Object { $_ }
    foreach ($base in $bases) {
        if (Test-Path -LiteralPath $base -PathType Container) {
            $executavel = Get-ChildItem -LiteralPath $base -Filter "msedgewebview2.exe" -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($executavel) { return $true }
        }
    }
    return $false
}

try {
    Set-Content -LiteralPath $log -Value ("Instalacao iniciada em {0:dd/MM/yyyy HH:mm:ss}" -f (Get-Date)) -Encoding UTF8
    if (-not [Environment]::Is64BitOperatingSystem) { throw "Este pacote exige Windows 10 ou 11 de 64 bits." }
    foreach ($arquivo in @($pythonInstalador, $webViewInstalador, $instalarDependencias, $instalarSistema, (Join-Path $raizPacote "sistema\sistema.zip"))) {
        if (-not (Test-Path -LiteralPath $arquivo -PathType Leaf)) { throw "Arquivo obrigatório ausente: $arquivo" }
    }

    $python = Encontrar-Python314
    if (-not $python) {
        Registrar "Instalando Python 3.14 x64..."
        $argumentos = @(
            "/quiet", "InstallAllUsers=0", "Include_launcher=1", "Include_pip=1",
            "Include_test=0", "Include_doc=0", "Shortcuts=0", "AssociateFiles=0",
            "PrependPath=0", "TargetDir=`"$pythonDestino`""
        )
        $processo = Start-Process -FilePath $pythonInstalador -ArgumentList $argumentos -Wait -PassThru
        if ($processo.ExitCode -ne 0) { throw "O instalador do Python retornou o código $($processo.ExitCode)." }
        $python = Encontrar-Python314
        if (-not $python) { throw "Python 3.14 x64 não foi localizado após a instalação." }
    } else { Registrar "Python 3.14 x64 já está instalado; etapa ignorada." }

    if (-not (Testar-WebView2)) {
        Registrar "Instalando Microsoft Edge WebView2..."
        $processo = Start-Process -FilePath $webViewInstalador -ArgumentList "/silent", "/install" -Wait -PassThru
        if ($processo.ExitCode -notin @(0, 1638)) { throw "O instalador do WebView2 retornou o código $($processo.ExitCode)." }
    } else { Registrar "Microsoft Edge WebView2 já está instalado; etapa ignorada." }

    Registrar "Preparando as bibliotecas do sistema sem usar a internet..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $instalarDependencias -PythonExe $python -DestinoVenv (Join-Path $pastaAplicacao ".venv") *>> $log
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível preparar as bibliotecas Python. Consulte instalacao.log." }

    Registrar "Instalando o Controle Financeiro..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $instalarSistema -DestinoAplicacao $pastaAplicacao -SemInterface *>> $log
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível copiar o sistema. Consulte instalacao.log." }

    Registrar "Instalação concluída com sucesso."
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Instalação concluída com sucesso.`n`nUse o atalho '$nomeAplicacao' na Área de Trabalho ou no Menu Iniciar.",
        $nomeAplicacao, "OK", "Information"
    ) | Out-Null
}
catch {
    Registrar ("ERRO: " + $_.Exception.Message)
    try {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show(
            "Não foi possível concluir a instalação.`n`n$($_.Exception.Message)`n`nConsulte:`n$log",
            $nomeAplicacao, "OK", "Error"
        ) | Out-Null
    } catch {}
    exit 1
}

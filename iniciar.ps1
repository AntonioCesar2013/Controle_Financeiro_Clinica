$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

function Encontrar-Python {
    $pythonLocal = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $pythonLocal) {
        return $pythonLocal
    }

    foreach ($comando in @("python.exe", "python3.exe", "py.exe")) {
        $encontrado = Get-Command $comando -ErrorAction SilentlyContinue
        if ($encontrado) {
            return $encontrado.Source
        }
    }

    $diretorioPython = Join-Path $env:LOCALAPPDATA "Python"
    if (Test-Path -LiteralPath $diretorioPython) {
        $encontrado = Get-ChildItem -LiteralPath $diretorioPython -Filter "python.exe" -Recurse -File -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($encontrado) {
            return $encontrado.FullName
        }
    }

    return $null
}

$pastaLogs = Join-Path $PSScriptRoot "dados\logs"
New-Item -ItemType Directory -Path $pastaLogs -Force | Out-Null
$execucao = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$logInicio = Join-Path $pastaLogs "inicio-$execucao.log"
$logSaida = Join-Path $pastaLogs "aplicativo-$execucao.log"
$logErros = Join-Path $pastaLogs "erros-$execucao.log"

function Mostrar-Falha($mensagem) {
    Add-Content -LiteralPath $logInicio -Value $mensagem -Encoding UTF8
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("Não foi possível iniciar o sistema.`nConsulte os registros em:`n$pastaLogs", "Controle Financeiro", "OK", "Error") | Out-Null
}

$pythonExecutavel = Encontrar-Python

if (-not $pythonExecutavel) {
    Write-Host "Python não foi encontrado neste computador." -ForegroundColor Red
    Write-Host "Instale o Python 3.10 ou superior e marque a opção 'Add Python to PATH'."
    Mostrar-Falha "Python não encontrado. Instale Python 3.10 ou superior."
    exit 1
}

Write-Host "Iniciando o Controle Financeiro da Clínica..." -ForegroundColor Cyan
Write-Host "Python: $pythonExecutavel"

try {
    $verificarDependencias = @'
import importlib
import sys

try:
    for nome in ('webview', 'dateutil', 'platformdirs', 'keyring', 'boto3',
                 'google.auth', 'google_auth_oauthlib', 'googleapiclient',
                 'google_auth_httplib2', 'httplib2'):
        importlib.import_module(nome)
except ImportError:
    sys.exit(1)
'@
    $ErrorActionPreference = "Continue"
    & $pythonExecutavel -c $verificarDependencias *> $logInicio
    $codigoDependencias = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($codigoDependencias -ne 0) {
        Write-Host "Preparando os componentes do sistema e de backup..." -ForegroundColor Yellow
        $ErrorActionPreference = "Continue"
        & $pythonExecutavel -m pip install -r requirements.txt *>> $logInicio
        $codigoInstalacao = $LASTEXITCODE
        $ErrorActionPreference = "Stop"
        if ($codigoInstalacao -ne 0) {
            throw "Não foi possível instalar os componentes do sistema e de backup."
        }
    }
    $executavelReal = & $pythonExecutavel -c "import sys; print(sys.executable)"
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível localizar o Python instalado." }
    $pythonJanela = Join-Path (Split-Path -Parent ($executavelReal | Select-Object -Last 1)) "pythonw.exe"
    if (-not (Test-Path -LiteralPath $pythonJanela)) { throw "Python sem console (pythonw.exe) não encontrado. Repare a instalação do Python." }
    $env:CLINICA_LOG_SAIDA = $logSaida
    $env:CLINICA_LOG_ERROS = $logErros
    $processo = Start-Process -FilePath $pythonJanela -ArgumentList "-u", "main.py" -WorkingDirectory $PSScriptRoot -WindowStyle Normal -PassThru

    # O PowerShell consome dezenas de MB. Mantenha-o somente durante a partida,
    # quando ainda precisamos apresentar erros; depois o aplicativo segue sozinho.
    $encerrouNaPartida = $processo.WaitForExit(5000)
    if (-not $encerrouNaPartida) {
        exit 0
    }
    if ($processo.ExitCode -eq 2) {
        Add-Content -LiteralPath $logInicio -Value "Abertura bloqueada: banco em uso ou indisponível." -Encoding UTF8
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show("O sistema já está aberto ou o banco está em uso. Verifique a janela do aplicativo na barra de tarefas. Se não houver janela, consulte o suporte antes de encerrar processos.", "Controle Financeiro", "OK", "Information") | Out-Null
        exit 0
    }
    if ($processo.ExitCode -ne 0) {
        throw "O processo terminou com o código $($processo.ExitCode). Consulte $logErros."
    }
}
catch {
    Write-Host "Não foi possível iniciar o sistema:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Mostrar-Falha $_.Exception.Message
    exit 1
}

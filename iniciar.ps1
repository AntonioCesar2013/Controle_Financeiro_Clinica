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

$pythonExecutavel = Encontrar-Python

if (-not $pythonExecutavel) {
    Write-Host "Python não foi encontrado neste computador." -ForegroundColor Red
    Write-Host "Instale o Python 3.10 ou superior e marque a opção 'Add Python to PATH'."
    Read-Host "Pressione Enter para fechar"
    exit 1
}

Write-Host "Iniciando o Controle Financeiro da Clínica..." -ForegroundColor Cyan
Write-Host "Python: $pythonExecutavel"

try {
    & $pythonExecutavel -c "import webview" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Preparando a interface WebView2..." -ForegroundColor Yellow
        & $pythonExecutavel -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            throw "Não foi possível instalar os componentes da interface WebView2."
        }
    }
    & $pythonExecutavel main.py
    if ($LASTEXITCODE -ne 0) {
        throw "O processo terminou com o código $LASTEXITCODE."
    }
}
catch {
    Write-Host "Não foi possível iniciar o sistema:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "Pressione Enter para fechar"
    exit 1
}

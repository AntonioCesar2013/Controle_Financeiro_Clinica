param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [string]$DestinoVenv = (Join-Path (Split-Path -Parent $PSScriptRoot) ".venv")
)

$ErrorActionPreference = "Stop"
$PythonExe = [System.IO.Path]::GetFullPath($PythonExe)
$DestinoVenv = [System.IO.Path]::GetFullPath($DestinoVenv)
$Wheels = Join-Path $PSScriptRoot "dependencias-python"
$Lock = Join-Path $PSScriptRoot "requirements-lock-win64-py314.txt"

if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Python não encontrado: $PythonExe"
}
if (-not (Test-Path -LiteralPath $Wheels -PathType Container)) {
    throw "Pasta de dependências não encontrada: $Wheels"
}

$Plataforma = & $PythonExe -c "import platform,struct,sys; print('%d.%d|%s|%d' % (sys.version_info.major,sys.version_info.minor,platform.machine(),struct.calcsize('P')*8))"
if ($LASTEXITCODE -ne 0 -or $Plataforma.Trim() -ne "3.14|AMD64|64") {
    throw "Este pacote exige Python 3.14 x64; encontrado: $Plataforma"
}

& $PythonExe -m venv $DestinoVenv
if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o ambiente virtual." }

$PythonVenv = Join-Path $DestinoVenv "Scripts\python.exe"
& $PythonVenv -m pip install --no-index --find-links $Wheels --requirement $Lock
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências offline." }

& $PythonVenv -c "import webview,dateutil,platformdirs,keyring,boto3,google.auth,google_auth_oauthlib,googleapiclient,google_auth_httplib2,httplib2; print('Dependências offline verificadas com sucesso.')"
if ($LASTEXITCODE -ne 0) { throw "As dependências foram instaladas, mas a verificação de imports falhou." }

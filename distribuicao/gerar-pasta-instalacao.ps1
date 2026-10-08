$ErrorActionPreference = "Stop"

$raizProjeto = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$destino = Join-Path $PSScriptRoot "ControleFinanceiroClinica-Instalacao"
$instaladorSistema = Join-Path $PSScriptRoot "instalador-sistema"
$buildSistema = Join-Path $instaladorSistema "build"

if (Test-Path -LiteralPath $destino) {
    $destinoResolvido = [IO.Path]::GetFullPath($destino)
    $basePermitida = [IO.Path]::GetFullPath($PSScriptRoot) + [IO.Path]::DirectorySeparatorChar
    if (-not $destinoResolvido.StartsWith($basePermitida, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Pasta de destino fora do diretório permitido."
    }
    Remove-Item -LiteralPath $destino -Recurse -Force
}

# O gerador do instalador também produz sistema.zip com a versão atual do código.
& (Join-Path $instaladorSistema "gerar-instalador.ps1")
if (-not (Test-Path -LiteralPath (Join-Path $buildSistema "sistema.zip") -PathType Leaf)) {
    throw "Não foi possível preparar o pacote do sistema."
}

New-Item -ItemType Directory -Path (Join-Path $destino "pre-requisitos") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $destino "dependencias-python") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $destino "sistema") -Force | Out-Null

foreach ($arquivo in @("INSTALAR.cmd", "instalar-completo.ps1", "instalar_dependencias_offline.ps1", "requirements-lock-win64-py314.txt", "LEIA-ME-INSTALACAO.txt")) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $arquivo) -Destination $destino -Force
}
Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot "pre-requisitos") -File |
    Copy-Item -Destination (Join-Path $destino "pre-requisitos") -Force
Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot "dependencias-python") -File |
    Copy-Item -Destination (Join-Path $destino "dependencias-python") -Force
Copy-Item -LiteralPath (Join-Path $buildSistema "sistema.zip") -Destination (Join-Path $destino "sistema\sistema.zip") -Force
Copy-Item -LiteralPath (Join-Path $buildSistema "instalar-sistema.ps1") -Destination (Join-Path $destino "sistema\instalar-sistema.ps1") -Force

$obrigatorios = @(
    "INSTALAR.cmd", "instalar-completo.ps1", "instalar_dependencias_offline.ps1",
    "requirements-lock-win64-py314.txt", "pre-requisitos\python-3.14.7-amd64.exe",
    "pre-requisitos\MicrosoftEdgeWebView2RuntimeInstallerX64.exe",
    "sistema\sistema.zip", "sistema\instalar-sistema.ps1"
)
foreach ($relativo in $obrigatorios) {
    if (-not (Test-Path -LiteralPath (Join-Path $destino $relativo) -PathType Leaf)) {
        throw "Pacote incompleto: $relativo"
    }
}

$wheels = Get-ChildItem -LiteralPath (Join-Path $destino "dependencias-python") -Filter "*.whl" -File
if ($wheels.Count -ne 43) { throw "Quantidade inesperada de dependências: $($wheels.Count)." }

$arquivos = Get-ChildItem -LiteralPath $destino -File -Recurse
$tamanho = ($arquivos | Measure-Object Length -Sum).Sum
$manifesto = $arquivos | Sort-Object FullName | ForEach-Object {
    $relativo = $_.FullName.Substring($destino.Length + 1)
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    "$hash  $relativo"
}
$manifesto | Set-Content -LiteralPath (Join-Path $destino "SHA256SUMS.txt") -Encoding UTF8

Write-Host "Pasta de instalação criada: $destino"
Write-Host "Arquivos: $($arquivos.Count)"
Write-Host ("Tamanho: {0:N2} MB" -f ($tamanho / 1MB))

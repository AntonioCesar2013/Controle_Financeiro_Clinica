$ErrorActionPreference = "Stop"

$raizProjeto = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pastaBuild = Join-Path $PSScriptRoot "build"
$pastaSistema = Join-Path $pastaBuild "sistema"
$arquivoZip = Join-Path $pastaBuild "sistema.zip"
$arquivoSed = Join-Path $pastaBuild "instalador.sed"
$saida = Join-Path $PSScriptRoot "ControleFinanceiroClinica-Setup.exe"
$saidaTemporaria = Join-Path $PSScriptRoot "ControleFinanceiroClinica-Setup.novo.exe"
$cabTemporario = Join-Path $PSScriptRoot "~ControleFinanceiroClinica-Setup.CAB"

if (Test-Path -LiteralPath $pastaBuild) {
    $resolvido = [IO.Path]::GetFullPath($pastaBuild)
    $basePermitida = [IO.Path]::GetFullPath($PSScriptRoot) + [IO.Path]::DirectorySeparatorChar
    if (-not $resolvido.StartsWith($basePermitida, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Pasta de build fora do diretório permitido."
    }
    Remove-Item -LiteralPath $pastaBuild -Recurse -Force
}

New-Item -ItemType Directory -Path $pastaSistema -Force | Out-Null

foreach ($artefatoAnterior in @($saida, $saidaTemporaria, $cabTemporario)) {
    if (Test-Path -LiteralPath $artefatoAnterior) {
        Remove-Item -LiteralPath $artefatoAnterior -Force
    }
}

foreach ($arquivo in @("main.py", "iniciar.ps1", "iniciar.cmd", "iniciar.vbs", "requirements.txt")) {
    Copy-Item -LiteralPath (Join-Path $raizProjeto $arquivo) -Destination $pastaSistema
}

Copy-Item -LiteralPath (Join-Path $raizProjeto "frontend") -Destination $pastaSistema -Recurse
Copy-Item -LiteralPath (Join-Path $raizProjeto "src") -Destination $pastaSistema -Recurse

Get-ChildItem -LiteralPath $pastaSistema -Directory -Recurse -Force |
    Where-Object Name -eq "__pycache__" |
    Sort-Object FullName -Descending |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $pastaSistema -File -Recurse -Force |
    Where-Object {
        $_.Extension -eq ".pyc" -or
        $_.Name -like "test*.py" -or
        $_.Name -in @("popular_banco.py", "popular_despesas_reais.py", "popular_entradas_reais.py")
    } |
    Remove-Item -Force

$scripts = Join-Path $pastaSistema "src\scripts"
if (Test-Path -LiteralPath $scripts) {
    Remove-Item -LiteralPath $scripts -Recurse -Force
}

Compress-Archive -Path (Join-Path $pastaSistema "*") -DestinationPath $arquivoZip -CompressionLevel Optimal
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "instalar-sistema.ps1") -Destination $pastaBuild

$sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$saidaTemporaria
FriendlyName=Controle Financeiro da Clinica
AppLaunched=powershell.exe -NoProfile -ExecutionPolicy Bypass -File instalar-sistema.ps1
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[Strings]
FILE0="instalar-sistema.ps1"
FILE1="sistema.zip"
[SourceFiles]
SourceFiles0=$pastaBuild\
[SourceFiles0]
%FILE0%=
%FILE1%=
"@

Set-Content -LiteralPath $arquivoSed -Value $sed -Encoding ASCII
& "$env:SystemRoot\System32\iexpress.exe" /N /Q $arquivoSed
$tamanhoMinimo = (Get-Item -LiteralPath $arquivoZip).Length
for ($tentativa = 0; $tentativa -lt 240; $tentativa++) {
    if ((Test-Path -LiteralPath $saidaTemporaria) -and
        (Get-Item -LiteralPath $saidaTemporaria).Length -gt $tamanhoMinimo) {
        break
    }
    Start-Sleep -Milliseconds 250
}
if (-not (Test-Path -LiteralPath $saidaTemporaria) -or
    (Get-Item -LiteralPath $saidaTemporaria).Length -le $tamanhoMinimo) {
    throw "O IExpress não conseguiu gerar o instalador."
}
Start-Sleep -Seconds 1
Copy-Item -LiteralPath $saidaTemporaria -Destination $saida -Force
Remove-Item -LiteralPath $saidaTemporaria -Force

if (Test-Path -LiteralPath $cabTemporario) {
    Remove-Item -LiteralPath $cabTemporario -Force
}

$arquivo = Get-Item -LiteralPath $saida
$hash = Get-FileHash -LiteralPath $saida -Algorithm SHA256
Write-Host "Instalador gerado: $($arquivo.FullName)"
Write-Host "Tamanho: $($arquivo.Length) bytes"
Write-Host "SHA-256: $($hash.Hash)"

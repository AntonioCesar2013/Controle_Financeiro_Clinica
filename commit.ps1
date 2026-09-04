param (
    [string]$Mensagem = ""
)

while ([string]::IsNullOrWhiteSpace($Mensagem)) {
    $Mensagem = Read-Host "Digite a mensagem do commit"
}

Write-Host ""
Write-Host "=== STATUS ATUAL ===" -ForegroundColor Cyan
git -C $PSScriptRoot status

Write-Host ""
Write-Host "=== ADICIONANDO ALTERACOES ===" -ForegroundColor Cyan
git -C $PSScriptRoot add .

Write-Host ""
Write-Host "=== STATUS APOS GIT ADD ===" -ForegroundColor Cyan
git -C $PSScriptRoot status

Write-Host ""
Write-Host "=== CRIANDO COMMIT ===" -ForegroundColor Cyan
git -C $PSScriptRoot commit -m $Mensagem

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Commit nao realizado." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "=== ENVIANDO PARA O GITHUB ===" -ForegroundColor Cyan
git -C $PSScriptRoot push

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Push falhou." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "=== CONCLUIDO ===" -ForegroundColor Green
git -C $PSScriptRoot status

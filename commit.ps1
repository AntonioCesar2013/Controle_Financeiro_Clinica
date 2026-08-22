param (
    [Parameter(Mandatory=$true)]
    [string]$Mensagem
)

Write-Host ""
Write-Host "=== STATUS ATUAL ===" -ForegroundColor Cyan
git status

Write-Host ""
Write-Host "=== ADICIONANDO ALTERACOES ===" -ForegroundColor Cyan
git add .

Write-Host ""
Write-Host "=== STATUS APOS GIT ADD ===" -ForegroundColor Cyan
git status

Write-Host ""
Write-Host "=== CRIANDO COMMIT ===" -ForegroundColor Cyan
git commit -m $Mensagem

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Commit nao realizado." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "=== ENVIANDO PARA O GITHUB ===" -ForegroundColor Cyan
git push

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Push falhou." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "=== CONCLUIDO ===" -ForegroundColor Green
git status
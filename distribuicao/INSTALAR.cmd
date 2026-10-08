@echo off
setlocal
title Instalacao - Controle Financeiro da Clinica
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar-completo.ps1"
if errorlevel 1 (
    echo.
    echo A instalacao nao foi concluida. Consulte o arquivo instalacao.log nesta pasta.
    pause
    exit /b 1
)
exit /b 0

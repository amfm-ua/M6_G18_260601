@echo off
cd /d "%~dp0"
title GrestelPy

if not exist "python\python.exe" (
    echo ERRO: Python portatil nao encontrado.
    echo Execute SETUP.bat primeiro.
    echo.
    pause
    exit /b 1
)

echo Servidor disponivel em: http://localhost:8000
echo Feche esta janela para parar o servidor.
echo.

python\python.exe server.py
pause

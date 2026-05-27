@echo off
cd /d "%~dp0"
title GrestelPy - Configuracao Inicial
echo ============================================
echo  GrestelPy - Configuracao Inicial
echo ============================================
echo.

:: Verificar se Python portatil existe e esta funcional
if exist "python\python.exe" (
    python\python.exe -c "import socket" >nul 2>&1
    if errorlevel 1 (
        echo Python portatil corrompido. A re-instalar...
        rmdir /s /q python
    ) else (
        echo Python portatil encontrado.
        goto install_packages
    )
)

:download_python
echo A descarregar Python portatil (aprox. 12 MB)...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip' -OutFile 'python_embed.zip' -UseBasicParsing"
if errorlevel 1 (
    echo.
    echo ERRO: Falha ao descarregar Python.
    echo Verifique a ligacao a internet e tente novamente.
    pause
    exit /b 1
)

echo A extrair Python...
powershell -Command "Expand-Archive -Path 'python_embed.zip' -DestinationPath 'python' -Force"
del python_embed.zip

:: Activate site-packages so pip works
powershell -Command "(Get-Content 'python\python312._pth') -replace '#import site', 'import site' | Set-Content 'python\python312._pth'"

echo A configurar pip...
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py' -UseBasicParsing"
python\python.exe get-pip.py --quiet
del get-pip.py

:install_packages
echo A instalar dependencias (pode demorar 3-5 minutos)...
python\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo ERRO: Falha ao instalar dependencias.
    echo A tentar re-instalar Python e dependencias...
    rmdir /s /q python
    goto download_python
)

echo.
echo ============================================
echo  Configuracao concluida!
echo  Execute start.bat para abrir o GrestelPy.
echo ============================================
echo.
pause

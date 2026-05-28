#!/bin/bash
echo "============================================"
echo " GrestelPy - Configuracao Inicial (Mac)"
echo "============================================"
echo ""

# Check for Python 3
if ! command -v python3 &>/dev/null; then
    echo "ERRO: Python 3 nao encontrado."
    echo ""
    echo "Instale Python 3 de uma das seguintes formas:"
    echo ""
    echo "  Opcao 1 — Homebrew (recomendado):"
    echo "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo "    brew install python"
    echo ""
    echo "  Opcao 2 — Instalador oficial:"
    echo "    https://www.python.org/downloads/"
    echo ""
    echo "Apos instalar Python 3, volte a correr este script."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "Python encontrado: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "A criar ambiente virtual..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERRO: Falha ao criar ambiente virtual."
        echo "Verifique se o modulo venv esta instalado: python3 -m ensurepip"
        exit 1
    fi
fi

echo "A activar ambiente virtual..."
source .venv/bin/activate

echo "A instalar dependencias (pode demorar alguns minutos)..."
pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo ""
    echo "ERRO: Falha ao instalar dependencias."
    echo "Verifique a ligacao a internet e tente novamente."
    exit 1
fi

echo ""
echo "============================================"
echo " Configuracao concluida!"
echo " Execute ./start-mac.sh para abrir o GrestelPy."
echo "============================================"
echo ""

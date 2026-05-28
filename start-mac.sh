#!/bin/bash
echo "A iniciar GrestelPy..."

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Ambiente virtual nao encontrado."
    echo "Execute ./setup-mac.sh primeiro."
    exit 1
fi

# Activate and ensure deps are current
source .venv/bin/activate
pip install -r requirements.txt --quiet

# Open browser after server starts
(sleep 2 && open http://localhost:8000 2>/dev/null) &

echo ""
echo "Servidor disponivel em: http://localhost:8000"
echo "Prima Ctrl+C para parar o servidor."
echo ""

python3 server.py

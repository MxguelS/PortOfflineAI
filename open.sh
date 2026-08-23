#!/usr/bin/env bash

set -e

# Directorio donde se encuentra PortOfflineAI
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

# Comprobar entorno virtual
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: no se encontró el entorno virtual de PortOfflineAI."
    echo
    echo "Ejecuta:"
    echo "  python -m venv .venv"
    echo "  .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Iniciar PortOfflineAI usando su entorno
exec "$VENV_PYTHON" src/main.py
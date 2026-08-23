import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"


def load_config():
    """Carga la configuración de PortOfflineAI."""
    if not CONFIG_PATH.exists():
        print(f"Error: no se encontró {CONFIG_PATH}")
        sys.exit(1)

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_files(config):
    """Comprueba que existan el runtime y el modelo."""
    runtime_path = PROJECT_ROOT / config["runtime"]["path"]
    model_path = PROJECT_ROOT / config["model"]["path"]

    if not runtime_path.exists():
        print("Error: no se encontró llama-server.")
        print(f"Ruta esperada: {runtime_path}")
        sys.exit(1)

    if not model_path.exists():
        print("Error: no se encontró el modelo.")
        print(f"Ruta esperada: {model_path}")
        sys.exit(1)

    return runtime_path, model_path
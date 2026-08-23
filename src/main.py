import json
import subprocess
import sys
from pathlib import Path


# Raíz del proyecto PortOfflineAI
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Archivo de configuración
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"


def load_config():
    """Carga la configuración de PortOfflineAI."""

    if not CONFIG_PATH.exists():
        print(f"Error: no se encontró {CONFIG_PATH}")
        sys.exit(1)

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def main():
    config = load_config()

    app_name = config["app"]["name"]
    version = config["app"]["version"]

    model_name = config["model"]["name"]
    model_path = PROJECT_ROOT / config["model"]["path"]

    runtime_path = PROJECT_ROOT / config["runtime"]["path"]

    print("=" * 40)
    print(f"       {app_name} v{version}")
    print("=" * 40)
    print()
    print(f"Modelo: {model_name}")
    print("Modo: Offline")
    print("Backend: CPU")
    print()

    # Verificar runtime
    if not runtime_path.exists():
        print("Error: no se encontró llama.cpp.")
        print(f"Ruta esperada: {runtime_path}")
        sys.exit(1)

    # Verificar modelo
    if not model_path.exists():
        print("Error: no se encontró el modelo.")
        print(f"Ruta esperada: {model_path}")
        sys.exit(1)

    print("Cargando modelo...")
    print()

    try:
        subprocess.run(
            [
                str(runtime_path),
                "-m",
                str(model_path),
            ],
            cwd=PROJECT_ROOT,
            check=True,
        )

    except KeyboardInterrupt:
        print("\nPortOfflineAI cerrado.")

    except subprocess.CalledProcessError as error:
        print(f"\nEl runtime terminó con un error: {error.returncode}")
        sys.exit(error.returncode)


if __name__ == "__main__":
    main()
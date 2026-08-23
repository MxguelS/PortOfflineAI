import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
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


def start_server(config, runtime_path, model_path):
    """Inicia llama-server en segundo plano."""
    host = config["runtime"]["host"]
    port = config["runtime"]["port"]

    command = [
        str(runtime_path),
        "-m",
        str(model_path),
        "--host",
        str(host),
        "--port",
        str(port),
    ]

    process = subprocess.Popen(
    command,
    cwd=PROJECT_ROOT,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    )

    return process


def wait_for_server(config, process, timeout=180):
    """Espera hasta que llama-server indique que está listo."""
    host = config["runtime"]["host"]
    port = config["runtime"]["port"]
    health_url = f"http://{host}:{port}/health"

    start_time = time.time()

    while time.time() - start_time < timeout:
        # Si llama-server murió durante la carga
        if process.poll() is not None:
            return False

        try:
            with urllib.request.urlopen(health_url, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("status") == "ok":
                    return True

        except (urllib.error.URLError, TimeoutError):
            pass

        time.sleep(1)

    return False


def send_message(config, messages):
    """Envía la conversación a la API local."""
    host = config["runtime"]["host"]
    port = config["runtime"]["port"]

    url = f"http://{host}:{port}/v1/chat/completions"

    payload = {
        "model": config["model"]["name"],
        "messages": messages,
        "max_tokens": 500,
    }

    request_data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result["choices"][0]["message"]["content"]


def chat(config):
    """Interfaz principal de conversación."""
    messages = []

    print()
    print("PortOfflineAI listo.")
    print("Escribe /exit para salir.")
    print()

    while True:
        try:
            user_input = input("> ").strip()

            if not user_input:
                continue

            if user_input.lower() == "/exit":
                break

            messages.append(
                {
                    "role": "user",
                    "content": user_input,
                }
            )

            print()
            print("Pensando...")

            response = send_message(config, messages)

            messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )

            print()
            print(response)
            print()

        except urllib.error.URLError as error:
            print()
            print(f"Error comunicándose con el modelo: {error}")
            print()


def main():
    config = load_config()

    app_name = config["app"]["name"]
    version = config["app"]["version"]
    model_name = config["model"]["name"]

    print("=" * 40)
    print(f"       {app_name} v{version}")
    print("=" * 40)
    print()
    print(f"Modelo: {model_name}")
    print("Modo: Offline")
    print("Backend: CPU")
    print()

    runtime_path, model_path = validate_files(config)

    print("Cargando modelo...")

    server_process = start_server(
        config,
        runtime_path,
        model_path,
    )

    try:
        if not wait_for_server(config, server_process):
            print("Error: llama-server no pudo iniciarse.")
            server_process.terminate()
            sys.exit(1)

        chat(config)

    except KeyboardInterrupt:
        print()

    finally:
        print("Cerrando PortOfflineAI...")

        if server_process.poll() is None:
            server_process.terminate()

            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()

        print("PortOfflineAI cerrado.")


if __name__ == "__main__":
    main()
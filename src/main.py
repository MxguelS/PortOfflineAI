import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
console = Console()

def show_header(config):
    """Muestra la cabecera principal de PortOfflineAI."""
    app_name = config["app"]["name"]
    version = config["app"]["version"]
    model_name = config["model"]["name"]

    console.print()
    console.print(f"[bold]{app_name}[/bold]                                      v{version}")
    console.rule(style="dim")
    console.print()
    console.print(f"[bold]Model[/bold]      {model_name}")
    console.print("[bold]Backend[/bold]    CPU")
    console.print("[bold]Mode[/bold]       Offline")
    console.print()


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


def show_help():
    """Muestra los comandos disponibles."""
    console.print()
    console.print("[bold]Commands[/bold]")
    console.print()
    console.print("  /help      Show available commands")
    console.print("  /clear     Clear conversation history")
    console.print("  /status    Show PortOfflineAI status")
    console.print("  /exit      Close PortOfflineAI")
    console.print()


def show_status(config):
    """Muestra el estado actual de PortOfflineAI."""
    console.print()
    console.print("[bold]Status[/bold]")
    console.print()
    console.print(f"  Version    {config['app']['version']}")
    console.print(f"  Model      {config['model']['name']}")
    console.print("  Backend    CPU")
    console.print("  Mode       Offline")
    console.print("  Server     Running")
    console.print()


def chat(config):
    """Interfaz principal de conversación."""
    messages = []

    console.rule(style="dim")
    console.print()
    console.print("[bold]Ready[/bold]")
    console.print("Type [bold]/help[/bold] to see available commands.")
    console.print()

    while True:
        try:
            console.print("[bold]You[/bold]")
            user_input = console.input("❯ ").strip()

            if not user_input:
                continue

            command = user_input.lower()

            if command == "/exit":
                break

            if command == "/help":
                show_help()
                continue

            if command == "/clear":
                messages.clear()
                console.print()
                console.print("Conversation cleared.")
                console.print()
                continue

            if command == "/status":
                show_status(config)
                continue

            messages.append(
                {
                    "role": "user",
                    "content": user_input,
                }
            )

            console.print()
            console.print("[bold]PortOfflineAI[/bold]")

            with console.status("Thinking...", spinner="dots"):
                response = send_message(config, messages)

            messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )

            console.print(Markdown(response))
            console.print()

        except urllib.error.URLError as error:
            console.print()
            console.print(f"Error communicating with the model: {error}")
            console.print()


def main():
    config = load_config()

    show_header(config)

    runtime_path, model_path = validate_files(config)

    server_process = None

    try:
        with console.status("Loading model...", spinner="dots"):
            server_process = start_server(
                config,
                runtime_path,
                model_path,
            )

            if not wait_for_server(config, server_process):
                console.print("Error: llama-server could not start.")
                sys.exit(1)

        chat(config)

    except KeyboardInterrupt:
        console.print()

    finally:
        console.print()
        console.print("Closing PortOfflineAI...")

        if server_process is not None and server_process.poll() is None:
            server_process.terminate()

            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()

        console.print("PortOfflineAI closed.")


if __name__ == "__main__":
    main()
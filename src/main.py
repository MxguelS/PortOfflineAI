import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
MAX_DOCUMENT_SIZE = 32 * 1024  # 32 KB

console = Console()


def show_header(config):
    """Muestra la cabecera principal de PortOfflineAI."""
    app_name = config["app"]["name"]
    version = config["app"]["version"]
    model_name = config["model"]["name"]

    console.print()
    console.print(
        f"[bold]{app_name}[/bold]                                      v{version}"
    )
    console.rule(style="dim")
    console.print()
    console.print(f"[bold]Model[/bold]      {model_name}")
    console.print("[bold]Backend[/bold]    CPU")
    console.print("[bold]Mode[/bold]       Offline")
    console.print()


def load_config():
    """Carga la configuración de PortOfflineAI."""
    if not CONFIG_PATH.exists():
        console.print(f"Error: no se encontró {CONFIG_PATH}")
        sys.exit(1)

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_files(config):
    """Comprueba que existan el runtime y el modelo."""
    runtime_path = PROJECT_ROOT / config["runtime"]["path"]
    model_path = PROJECT_ROOT / config["model"]["path"]

    if not runtime_path.exists():
        console.print("Error: no se encontró llama-server.")
        console.print(f"Ruta esperada: {runtime_path}")
        sys.exit(1)

    if not model_path.exists():
        console.print("Error: no se encontró el modelo.")
        console.print(f"Ruta esperada: {model_path}")
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
        "--reasoning",
        "off",
        "--parallel",
        "1",
        "--ctx-size",
        "8192",
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
        "max_tokens": 2048,
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

    message = result["choices"][0]["message"]["content"]

    usage = result.get("usage", {})
    timings = result.get("timings", {})

    metrics = {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "tokens_per_second": timings.get("predicted_per_second", 0),
        "finish_reason": result["choices"][0].get(
            "finish_reason",
            "unknown",
        ),
    }

    return message, metrics


def show_help():
    """Muestra los comandos disponibles."""
    console.print()
    console.print("[bold]Commands[/bold]")
    console.print()
    console.print("  /help           Show available commands")
    console.print("  /clear          Clear conversation history")
    console.print("  /status         Show PortOfflineAI status")
    console.print("  /docs           Show available documents")
    console.print("  /read <file>    Load a local document")
    console.print("  /unload         Unload active document")
    console.print("  /exit           Close PortOfflineAI")
    console.print()


def show_status(config, active_document):
    """Muestra el estado actual de PortOfflineAI."""
    console.print()
    console.print("[bold]Status[/bold]")
    console.print()
    console.print(f"  Version     {config['app']['version']}")
    console.print(f"  Model       {config['model']['name']}")
    console.print("  Backend     CPU")
    console.print("  Mode        Offline")
    console.print("  Server      Running")

    if active_document:
        console.print(f"  Document    {active_document['name']}")
    else:
        console.print("  Document    None")

    console.print()

def show_documents():
    """Muestra los documentos disponibles en knowledge/."""
    console.print()
    console.print("[bold]Documents[/bold]")
    console.print()

    if not KNOWLEDGE_DIR.exists():
        console.print("  Knowledge directory not found.")
        console.print()
        return

    documents = sorted(
        file
        for file in KNOWLEDGE_DIR.iterdir()
        if file.is_file()
        and file.suffix.lower() in {".txt", ".md"}
    )

    if not documents:
        console.print("  No documents available.")
        console.print()
        return

    for index, document in enumerate(documents, start=1):
        console.print(f"  {index}. {document.name}")

    console.print()


def read_document(filename):
    """Lee un documento desde knowledge/."""
    file_path = KNOWLEDGE_DIR / filename

    if not file_path.exists():
        return None, f"Document not found: {filename}"

    if not file_path.is_file():
        return None, f"Not a valid document: {filename}"

    if file_path.suffix.lower() not in {".txt", ".md"}:
        return None, "Only .txt and .md documents are supported."

    try:
        file_size = file_path.stat().st_size

        if file_size > MAX_DOCUMENT_SIZE:
            max_kb = MAX_DOCUMENT_SIZE // 1024

            return None, (
                f"Document is too large. "
                f"Maximum supported size is {max_kb} KB."
            )

        content = file_path.read_text(encoding="utf-8")

    except (OSError, UnicodeDecodeError) as error:
        return None, f"Could not read document: {error}"

    return content, None

def chat(config):
    """Interfaz principal de conversación."""
    messages = []
    active_document = None

    console.rule(style="dim")
    console.print()
    console.print("[bold]Ready[/bold]")
    console.print(
        "Type [bold]/help[/bold] to see available commands."
    )
    console.print()

    while True:
        try:
            console.print("[bold]You[/bold]")
            user_input = console.input("❯ ").strip()

            if not user_input:
                continue

            command = user_input.lower()

            # -------------------------
            # Comandos internos
            # -------------------------

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
                show_status(config, active_document)
                continue

            if command == "/docs":
                show_documents()
                continue

            if command.startswith("/read "):
                filename = user_input[6:].strip()

                content, error = read_document(filename)

                if error:
                    console.print()
                    console.print(
                        f"[bold]Error[/bold]: {error}"
                    )
                    console.print()
                    continue

                active_document = {
                    "name": filename,
                    "content": content,
                }

                console.print()
                console.print(
                    f"Loaded document: [bold]{filename}[/bold]"
                )
                console.print()

                continue

            if command == "/unload":
                if active_document is None:
                    console.print()
                    console.print(
                        "No document is currently loaded."
                    )
                    console.print()
                    continue

                document_name = active_document["name"]
                active_document = None

                console.print()
                console.print(
                    f"Unloaded document: "
                    f"[bold]{document_name}[/bold]"
                )
                console.print()

                continue

            # -------------------------
            # Construcción del contexto
            # -------------------------

            request_messages = []

            if active_document:
                request_messages.append(
                    {
                        "role": "system",
                        "content": (
                            "You have access to the following "
                            "local document. Use it when it is "
                            "relevant to answer the user.\n\n"
                            f"Document: "
                            f"{active_document['name']}\n"
                            f"Content:\n"
                            f"{active_document['content']}"
                        ),
                    }
                )

            # Historial anterior
            request_messages.extend(messages)

            # Mensaje actual
            user_message = {
                "role": "user",
                "content": user_input,
            }

            messages.append(user_message)
            request_messages.append(user_message)

            # -------------------------
            # Generación
            # -------------------------

            console.print()
            console.print("[bold]PortOfflineAI[/bold]")

            with console.status(
                "Thinking...",
                spinner="dots",
            ):
                start_time = time.perf_counter()

                response, metrics = send_message(
                    config,
                    request_messages,
                )

                elapsed_time = (
                    time.perf_counter() - start_time
                )

            # Guardar respuesta en historial
            messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )

            # Mostrar respuesta
            console.print(Markdown(response))
            console.print()

            console.print(
                f"[dim]Generated in {elapsed_time:.1f}s · "
                f"{metrics['completion_tokens']} tokens · "
                f"{metrics['tokens_per_second']:.1f} tok/s · "
                f"{metrics['finish_reason']}[/dim]"
            )

        except urllib.error.URLError as error:
            console.print()
            console.print(
                f"Error communicating with the model: {error}"
            )
            console.print()


def main():
    config = load_config()

    show_header(config)

    runtime_path, model_path = validate_files(config)

    server_process = None

    try:
        with console.status(
            "Loading model...",
            spinner="dots",
        ):
            server_process = start_server(
                config,
                runtime_path,
                model_path,
            )

            if not wait_for_server(
                config,
                server_process,
            ):
                console.print(
                    "Error: llama-server could not start."
                )
                sys.exit(1)

        chat(config)

    except KeyboardInterrupt:
        console.print()

    finally:
        console.print()
        console.print("Closing PortOfflineAI...")

        if (
            server_process is not None
            and server_process.poll() is None
        ):
            server_process.terminate()

            try:
                server_process.wait(timeout=10)

            except subprocess.TimeoutExpired:
                server_process.kill()

        console.print("PortOfflineAI closed.")


if __name__ == "__main__":
    main()
from rich.console import Console
from rich.markdown import Markdown
from src.modes import get_mode

from src.documents import get_documents


console = Console()


def show_header(config):
    """Muestra la cabecera principal."""
    app_name = config["app"]["name"]
    version = config["app"]["version"]
    model_name = config["model"]["name"]

    console.print()
    console.print(
        f"[bold]{app_name}[/bold]"
        f"                                      v{version}"
    )
    console.rule(style="dim")
    console.print()
    console.print(f"[bold]Model[/bold]      {model_name}")
    console.print("[bold]Backend[/bold]    CPU")
    console.print("[bold]Connectivity[/bold]  Offline")
    console.print()


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
    console.print("  /mode           Show available modes")
    console.print("  /mode <mode>    Change active mode")
    console.print("  /project <path>   Load a local project")
    console.print("  /project          Show active project")
    console.print("  /project unload   Unload active project")
    console.print("  /files            Show project files")
    console.print("  /context              Show context files")
    console.print("  /context add <file>   Add file to context")
    console.print("  /context remove <file> Remove file from context")
    console.print("  /context clear        Clear context files")

    console.print()


def show_status(config, active_document, active_mode):
    """Muestra el estado de PortOfflineAI."""
    console.print()
    console.print("[bold]Status[/bold]")
    console.print()

    console.print(f"  Version       {config['app']['version']}")
    console.print(f"  Model         {config['model']['name']}")
    console.print("  Backend       CPU")
    console.print("  Connectivity  Offline")
    mode = get_mode(active_mode)
    mode_name = mode["name"] if mode else active_mode
    console.print(f"  AI Mode       {mode_name}")
    console.print("  Server        Running")

    if active_document:
        console.print(
            f"  Document      {active_document['name']}"
        )
    else:
        console.print("  Document      None")

    console.print()


def show_documents():
    """Muestra los documentos disponibles."""
    documents = get_documents()

    console.print()
    console.print("[bold]Documents[/bold]")
    console.print()

    if not documents:
        console.print("  No documents available.")
        console.print()
        return

    for index, document in enumerate(
        documents,
        start=1,
    ):
        console.print(f"  {index}. {document.name}")

    console.print()


def show_response(response):
    """Renderiza una respuesta Markdown."""
    console.print(Markdown(response))
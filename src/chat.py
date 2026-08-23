import time
import urllib.error

from src.api import send_message
from src.documents import read_document
from src.ui import (
    console,
    show_documents,
    show_help,
    show_response,
    show_status,
)
from src.modes import (
    DEFAULT_MODE,
    get_available_modes,
    get_mode,
    get_system_prompt,
    mode_exists,
)


class ChatSession:
    """Gestiona una sesión de conversación."""

    def __init__(self, config):
        self.config = config
        self.messages = []
        self.active_document = None
        configured_mode = config["app"].get("default_mode", DEFAULT_MODE)
        if mode_exists(configured_mode):
            self.active_mode = configured_mode
        else:
            self.active_mode = DEFAULT_MODE

    def clear(self):
        """Limpia el historial de conversación."""
        self.messages.clear()

        console.print()
        console.print("Conversation cleared.")
        console.print()

    def show_modes(self):
        """Muestra el modo actual y los modos disponibles."""
        modes = get_available_modes()

        console.print()
        console.print("[bold]Modes[/bold]")
        console.print()

        for mode_id, mode in modes.items():
            marker = "*" if mode_id == self.active_mode else " "

            console.print(
                f" {marker} {mode_id:<10} "
                f"{mode['name']} - {mode['description']}"
            )

        console.print()
        console.print(
            f"Current mode: "
            f"[bold]{get_mode(self.active_mode)['name']}[/bold]"
        )
        console.print()


    def change_mode(self, mode_id):
        """Cambia el modo activo de la sesión."""
        mode_id = mode_id.lower().strip()

        if not mode_exists(mode_id):
            console.print()
            console.print(
                f"[bold]Error[/bold]: Unknown mode: {mode_id}"
            )
            console.print()
            console.print(
                "Use [bold]/mode[/bold] to see available modes."
            )
            console.print()
            return

        if mode_id == self.active_mode:
            console.print()
            console.print(
                f"Mode already active: "
                f"[bold]{get_mode(mode_id)['name']}[/bold]"
            )
            console.print()
            return

        self.active_mode = mode_id

        # Evitamos mezclar una conversación mantenida bajo
        # instrucciones de otro modo.
        self.messages.clear()

        console.print()
        console.print(
            f"Mode changed to: "
            f"[bold]{get_mode(mode_id)['name']}[/bold]"
        )
        console.print("Conversation history cleared.")
        console.print()
    
    

    def load_document(self, filename):
        """Carga un documento local."""

        content, error = read_document(filename)

        if error:
            console.print()
            console.print(f"[bold]Error[/bold]: {error}")
            console.print()
            return

        self.active_document = {
            "name": filename,
            "content": content,
        }

        # El nuevo documento inicia un contexto limpio
        self.messages.clear()

        console.print()
        console.print(f"Loaded document: [bold]{filename}[/bold]")
        console.print("Conversation history cleared.")
        console.print()

    def unload_document(self):
        """Descarga el documento activo."""

        if self.active_document is None:
            console.print()
            console.print("No document is currently loaded.")
            console.print()
            return

        filename = self.active_document["name"]

        self.active_document = None

        # Evita conservar contexto del documento anterior
        self.messages.clear()

        console.print()
        console.print(f"Unloaded document: [bold]{filename}[/bold]")
        console.print("Conversation history cleared.")
        console.print()

    def build_request(self, user_input):
        """Construye el contexto enviado al modelo."""
        request_messages = [
            {
                "role": "system",
                "content": get_system_prompt(self.active_mode),
            }
        ]

        if self.active_document:
            request_messages.append(
                {
                    "role": "system",
                    "content": (
                        "You have access to the following "
                        "local document. Use it when it is "
                        "relevant to answer the user.\n\n"
                        f"Document: "
                        f"{self.active_document['name']}\n"
                        f"Content:\n"
                        f"{self.active_document['content']}"
                    ),
                }
            )

        request_messages.extend(self.messages)

        user_message = {
            "role": "user",
            "content": user_input,
        }

        self.messages.append(user_message)
        request_messages.append(user_message)

        return request_messages

    def generate_response(self, request_messages):
            """Genera y muestra una respuesta."""
            console.print()
            console.print("[bold]PortOfflineAI[/bold]")

            with console.status(
                "Thinking...",
                spinner="dots",
            ):
                start_time = time.perf_counter()

                response, metrics = send_message(
                    self.config,
                    request_messages,
                )

                elapsed_time = (
                    time.perf_counter() - start_time
                )

            self.messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )

            show_response(response)

            console.print()

            console.print(
                f"[dim]Generated in {elapsed_time:.1f}s · "
                f"{metrics['completion_tokens']} tokens · "
                f"{metrics['tokens_per_second']:.1f} tok/s · "
                f"{metrics['finish_reason']}[/dim]"
            )

    def handle_command(self, user_input):
        """
        Procesa comandos.

        Retorna:
        - "exit" para cerrar.
        - True si era un comando.
        - False si debe enviarse al modelo.
        """
        command = user_input.lower()

        if command == "/exit":
            return "exit"

        if command == "/help":
            show_help()
            return True

        if command == "/clear":
            self.clear()
            return True

        if command == "/status":
            show_status(
                self.config,
                self.active_document,
                self.active_mode,
            )
            return True

        if command == "/docs":
            show_documents()
            return True

        if command.startswith("/read "):
            filename = user_input[6:].strip()

            self.load_document(filename)
            return True

        if command == "/unload":
            self.unload_document()
            return True
        if command == "/mode":
            self.show_modes()
            return True

        if command.startswith("/mode "):
            mode_id = user_input[6:].strip()

            if not mode_id:
                self.show_modes()
                return True

            self.change_mode(mode_id)
            return True
        if user_input.startswith("/"):
            console.print()
            console.print(
                f"[bold]Error[/bold]: Unknown command: {user_input}"
            )
            console.print(
                "Use [bold]/help[/bold] to see available commands."
            )
            console.print()
            return True


        return False

    def run(self):
        """Ejecuta la interfaz principal del chat."""
        console.rule(style="dim")
        console.print()
        console.print("[bold]Ready[/bold]")
        console.print(
            "Type [bold]/help[/bold] "
            "to see available commands."
        )
        console.print()

        while True:
            try:
                console.print("[bold]You[/bold]")
                user_input = console.input("❯ ").strip()

                if not user_input:
                    continue

                command_result = self.handle_command(
                    user_input
                )

                if command_result == "exit":
                    break

                if command_result is True:
                    continue

                request_messages = self.build_request(
                    user_input
                )

                self.generate_response(
                    request_messages
                )

            except urllib.error.URLError as error:
                console.print()
                console.print(
                    f"Error communicating with "
                    f"the model: {error}"
                )
                console.print()
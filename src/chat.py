import time
import urllib.error

from src.api import APIError, send_message
from src.documents import read_document
from src.projects import (
    get_project_files,
    load_project as resolve_project,
    resolve_project_file,
)
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
from src.chunking import (
    chunk_python_file,
    select_global_chunks,
    get_dependency_context,
)


MAX_CONTEXT_SIZE = 8 * 1024

class ChatSession:
    """Gestiona una sesión de conversación."""

    def __init__(self, config):
        self.config = config
        self.messages = []
        self.active_document = None
        self.active_project = None
        self.context_files = []
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
        """Carga un documento local o un archivo del proyecto activo."""

        # Si existe un proyecto activo, buscamos dentro del proyecto.
        if self.active_project is not None:
            file_path, error = resolve_project_file(
                self.active_project,
                filename,
            )

            if error:
                console.print()
                console.print(f"[bold]Error[/bold]: {error}")
                console.print()
                return

            try:
                file_size = file_path.stat().st_size

                if file_size > 32 * 1024:
                    console.print()
                    console.print(
                        "[bold]Error[/bold]: File is too large. "
                        "Maximum supported size is 32 KB."
                    )
                    console.print()
                    return

                content = file_path.read_text(encoding="utf-8")

            except UnicodeDecodeError:
                console.print()
                console.print(
                    "[bold]Error[/bold]: File is not valid UTF-8 text."
                )
                console.print()
                return

            except OSError as error:
                console.print()
                console.print(
                    f"[bold]Error[/bold]: Could not read file: {error}"
                )
                console.print()
                return

            document_name = str(
                file_path.relative_to(self.active_project)
            )

        # Sin proyecto mantenemos exactamente el comportamiento anterior.
        else:
            content, error = read_document(filename)

            if error:
                console.print()
                console.print(f"[bold]Error[/bold]: {error}")
                console.print()
                return

            document_name = filename

        self.active_document = {
            "name": document_name,
            "content": content,
        }

        self.messages.clear()

        console.print()
        console.print(
            f"Loaded document: [bold]{document_name}[/bold]"
        )
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


    def load_project(self, path):
        """Carga un proyecto local."""

        project_path, error = resolve_project(path)

        if error:
            console.print()
            console.print(f"[bold]Error[/bold]: {error}")
            console.print()
            return

        self.active_project = project_path
        self.active_document = None
        self.context_files.clear()
        self.messages.clear()

        console.print()
        console.print(
            f"Loaded project: [bold]{project_path.name}[/bold]"
        )
        console.print(f"Path: {project_path}")
        console.print("Conversation history cleared.")
        console.print()


    def unload_project(self):
        """Descarga el proyecto activo."""

        if self.active_project is None:
            console.print()
            console.print("No project is currently loaded.")
            console.print()
            return

        project_name = self.active_project.name

        self.active_project = None
        self.active_document = None
        self.context_files.clear()
        self.messages.clear()

        console.print()
        console.print(
            f"Unloaded project: [bold]{project_name}[/bold]"
        )
        console.print("Conversation history cleared.")
        console.print()


    def show_project(self):
        """Muestra el proyecto activo."""

        console.print()

        if self.active_project is None:
            console.print("No project is currently loaded.")
        else:
            console.print("[bold]Active Project[/bold]")
            console.print()
            console.print(f"  Name    {self.active_project.name}")
            console.print(f"  Path    {self.active_project}")

        console.print()


    def show_project_files(self):
        """Muestra los archivos soportados del proyecto activo."""

        if self.active_project is None:
            console.print()
            console.print(
                "[bold]Error[/bold]: No project is currently loaded."
            )
            console.print()
            return

        files = get_project_files(self.active_project)

        console.print()
        console.print("[bold]Project Files[/bold]")
        console.print()

        if not files:
            console.print("  No supported files found.")
            console.print()
            return

        visible_files = files[:200]

        for index, file in enumerate(visible_files, start=1):
            console.print(f"  {index}. {file}")

        if len(files) > len(visible_files):
            hidden_count = len(files) - len(visible_files)

            console.print()
            console.print(
                f"  ... and {hidden_count} more files."
            )

        console.print()
    
    def show_context(self):
            """Muestra los archivos cargados en el contexto."""

            console.print()
            console.print("[bold]Context Files[/bold]")
            console.print()

            if not self.context_files:
                console.print("  No files in context.")
                console.print()
                return

            for index, file in enumerate(
                self.context_files,
                start=1,
            ):
                console.print(
                    f"  {index}. {file['name']}"
                )
            total_size = sum(
                len(file["content"].encode("utf-8"))
                for file in self.context_files
            )

            console.print()
            console.print(
                f"Total: {len(self.context_files)} file(s)"
            )
            console.print("Smart Context: enabled")
            console.print(
                f"Budget: {MAX_CONTEXT_SIZE / 1024:.0f} KB"
            )
            console.print()


    def add_context_file(self, filename):
        """Añade un archivo del proyecto al contexto."""

        if self.active_project is None:
            console.print()
            console.print(
                "[bold]Error[/bold]: "
                "No project is currently loaded."
            )
            console.print()
            return

        file_path, error = resolve_project_file(
            self.active_project,
            filename,
        )

        if error:
            console.print()
            console.print(f"[bold]Error[/bold]: {error}")
            console.print()
            return

        document_name = str(
            file_path.relative_to(self.active_project)
        )

        # Evitar duplicados.
        for file in self.context_files:
            if file["name"] == document_name:
                console.print()
                console.print(
                    f"File already in context: "
                    f"[bold]{document_name}[/bold]"
                )
                console.print()
                return

        try:
            file_size = file_path.stat().st_size

            if file_size > 32 * 1024:
                console.print()
                console.print(
                    "[bold]Error[/bold]: File is too large. "
                    "Maximum supported size is 32 KB."
                )
                console.print()
                return

            content = file_path.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:
            console.print()
            console.print(
                "[bold]Error[/bold]: "
                "File is not valid UTF-8 text."
            )
            console.print()
            return

        except OSError as error:
            console.print()
            console.print(
                f"[bold]Error[/bold]: "
                f"Could not read file: {error}"
            )
            console.print()
            return
        current_size = sum(
            len(file["content"].encode("utf-8"))
            for file in self.context_files
        )

        new_file_size = len(content.encode("utf-8"))

        self.context_files.append(
            {
                "name": document_name,
                "path": file_path,
                "content": content,
            }
        )

        # El contexto de la conversación anterior ya no
        # representa exactamente los archivos actuales.
        self.messages.clear()

        console.print()
        console.print(
            f"Added to context: "
            f"[bold]{document_name}[/bold]"
        )
        console.print("Conversation history cleared.")
        console.print()


    def remove_context_file(self, filename):
        """Elimina un archivo del contexto."""

        filename = filename.strip()

        for index, file in enumerate(self.context_files):
            if file["name"] == filename:
                removed = self.context_files.pop(index)

                self.messages.clear()

                console.print()
                console.print(
                    f"Removed from context: "
                    f"[bold]{removed['name']}[/bold]"
                )
                console.print(
                    "Conversation history cleared."
                )
                console.print()
                return

        console.print()
        console.print(
            f"[bold]Error[/bold]: "
            f"File is not in context: {filename}"
        )
        console.print()


    def clear_context(self):
        """Elimina todos los archivos del contexto."""

        if not self.context_files:
            console.print()
            console.print("Context is already empty.")
            console.print()
            return

        self.context_files.clear()
        self.messages.clear()

        console.print()
        console.print("Context cleared.")
        console.print("Conversation history cleared.")
        console.print()

    def build_smart_context(self, user_input):
        """
        Construye contexto relevante combinando
        ranking global y análisis de dependencias.
        """

        file_chunks = []
        file_contents = {}
        fallback_files = []

        for file in self.context_files:
            file_path = file["path"]
            content = file["content"]

            file_contents[file["name"]] = content

            if file_path.suffix.lower() == ".py":
                chunks, error = chunk_python_file(
                    file_path
                )

                if not error and chunks:
                    file_chunks.append(
                        (
                            file["name"],
                            chunks,
                        )
                    )
                    continue

            fallback_files.append(file)

        ranked_chunks = select_global_chunks(
            file_chunks,
            user_input,
            max_size=MAX_CONTEXT_SIZE,
        )

        dependency_chunks = get_dependency_context(
            file_chunks,
            file_contents,
            user_input,
        )

        # Dependency chunks tienen prioridad porque
        # representan relaciones verificadas por AST.
        candidates = []

        for chunk in dependency_chunks:
            candidates.append(
                {
                    **chunk,
                    "source": "dependency",
                }
            )

        for chunk in ranked_chunks:
            candidates.append(
                {
                    **chunk,
                    "source": "ranking",
                }
            )

        # Evita que el mismo chunk entre dos veces.
        unique_chunks = []
        seen = set()

        for chunk in candidates:
            key = (
                chunk["file"],
                chunk["name"],
                chunk["start_line"],
                chunk["end_line"],
            )

            if key in seen:
                continue

            seen.add(key)
            unique_chunks.append(chunk)

        context_parts = []
        total_size = 0
        selected_count = 0

        for chunk in unique_chunks:
            if selected_count >= 6:
                break

            dependency_module = chunk.get(
                "dependency_module"
            )

            dependency_info = ""

            if dependency_module:
                dependencies = ", ".join(
                    chunk.get(
                        "dependencies",
                        [],
                    )
                )

                dependency_info = (
                    f"\nDependency: "
                    f"{dependency_module}"
                    f" via {dependencies}"
                )

            part = (
                f"File: {chunk['file']}\n"
                f"Chunk: {chunk['name']} "
                f"(lines {chunk['start_line']}-"
                f"{chunk['end_line']})"
                f"{dependency_info}\n"
                f"{chunk['content']}"
            )

            part_size = len(
                part.encode("utf-8")
            )

            if (
                total_size + part_size
                > MAX_CONTEXT_SIZE
            ):
                continue

            context_parts.append(part)
            total_size += part_size
            selected_count += 1

        # Archivos que todavía no tienen chunking.
        for file in fallback_files:
            if selected_count >= 6:
                break

            part = (
                f"File: {file['name']}\n"
                f"{file['content']}"
            )

            part_size = len(
                part.encode("utf-8")
            )

            if (
                total_size + part_size
                > MAX_CONTEXT_SIZE
            ):
                continue

            context_parts.append(part)
            total_size += part_size
            selected_count += 1
            
        return "\n\n---\n\n".join(
            context_parts
        )

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

        if self.context_files:
            smart_context = self.build_smart_context(
                user_input
            )

            if smart_context:
                request_messages.append(
                    {
                        "role": "system",
                        "content": (
                            "You have access to relevant parts "
                            "of files from the user's local project. "
                            "Use only the provided code as evidence. "
                            "Do not assume relationships or functions "
                            "that are not shown in the context.\n\n"
                            f"{smart_context}"
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
                try:
                    response, metrics = send_message(
                        self.config,
                        request_messages,
                    )

                except APIError as error:
                    console.print()
                    console.print(
                        f"[bold]Error[/bold]: {error}"
                    )
                    console.print()
                    return

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
        """Procesa los comandos de la CLI."""

        command = user_input.lower()

        # Comandos básicos
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

        # Documentos
        if command.startswith("/read "):
            filename = user_input[6:].strip()
            self.load_document(filename)
            return True

        if command == "/unload":
            self.unload_document()
            return True

        # Modos
        if command == "/mode":
            self.show_modes()
            return True

        if command.startswith("/mode "):
            mode_id = user_input[6:].strip()
            self.change_mode(mode_id)
            return True

        # Proyectos
        if command == "/project":
            self.show_project()
            return True

        if command.startswith("/project "):
            argument = user_input[9:].strip()

            if argument.lower() == "unload":
                self.unload_project()
            else:
                self.load_project(argument)

            return True

        if command == "/files":
            self.show_project_files()
            return True
                # Contexto múltiple

        if command == "/context":
            self.show_context()
            return True

        if command == "/context clear":
            self.clear_context()
            return True

        if command.startswith("/context add "):
            filename = user_input[13:].strip()

            if not filename:
                console.print()
                console.print(
                    "[bold]Error[/bold]: "
                    "A file path is required."
                )
                console.print()
                return True

            self.add_context_file(filename)
            return True

        if command.startswith("/context remove "):
            filename = user_input[16:].strip()

            if not filename:
                console.print()
                console.print(
                    "[bold]Error[/bold]: "
                    "A file path is required."
                )
                console.print()
                return True

            self.remove_context_file(filename)
            return True

        # Salir
        if command == "/exit":
            return "exit"

        # IMPORTANTE: esto tiene que ir AL FINAL
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
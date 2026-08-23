import sys

from src.chat import ChatSession
from src.config import load_config, validate_files
from src.server import LlamaServer
from src.ui import console, show_header


def main():
    """Punto de entrada de PortOfflineAI."""
    config = load_config()

    show_header(config)

    runtime_path, model_path = validate_files(config)

    server = LlamaServer(
        config,
        runtime_path,
        model_path,
    )

    try:
        with console.status(
            "Loading model...",
            spinner="dots",
        ):
            server.start()

            if not server.wait_until_ready():
                console.print(
                    "Error: llama-server could not start."
                )
                sys.exit(1)

        chat = ChatSession(config)
        chat.run()

    except KeyboardInterrupt:
        console.print()

    finally:
        console.print()
        console.print("Closing PortOfflineAI...")

        server.stop()

        console.print("PortOfflineAI closed.")


if __name__ == "__main__":
    main()
from pathlib import Path

from src.config import PROJECT_ROOT


KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
MAX_DOCUMENT_SIZE = 32 * 1024
SUPPORTED_EXTENSIONS = {
    # Documents
    ".txt",
    ".md",

    # Programming
    ".py",
    ".java",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".sh",

    # Web
    ".html",
    ".css",
    ".scss",

    # Data / configuration
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".sql",
}
SUPPORTED_FILENAMES = {
    "Dockerfile",
    "Makefile",
}

def get_documents():
    """Devuelve los documentos disponibles."""
    if not KNOWLEDGE_DIR.exists():
        return []

    return sorted(
        file
        for file in KNOWLEDGE_DIR.iterdir()
        if file.is_file()
        and file.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def read_document(filename):
    """Lee un documento desde knowledge/."""
    file_path = KNOWLEDGE_DIR / filename

    if not file_path.exists():
        return None, f"Document not found: {filename}"

    if not file_path.is_file():
        return None, f"Not a valid document: {filename}"

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return (
            None,
            f"Unsupported document type: {file_path.suffix}",
        )

    try:
        file_size = file_path.stat().st_size

        if file_size > MAX_DOCUMENT_SIZE:
            max_kb = MAX_DOCUMENT_SIZE // 1024

            return (
                None,
                f"Document is too large. "
                f"Maximum supported size is {max_kb} KB.",
            )

        content = file_path.read_text(encoding="utf-8")

    except (OSError, UnicodeDecodeError) as error:
        return None, f"Could not read document: {error}"

    return content, None

def is_supported_file(file_path):
    """Comprueba si un archivo puede cargarse como contexto."""
    return (
        file_path.suffix.lower() in SUPPORTED_EXTENSIONS
        or file_path.name in SUPPORTED_FILENAMES
    )
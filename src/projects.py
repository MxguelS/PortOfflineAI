"""Gestión de proyectos locales para PortOfflineAI."""

from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".py", ".java", ".js", ".ts", ".jsx", ".tsx",
    ".c", ".h", ".cpp", ".hpp", ".cs",
    ".go", ".rs", ".php", ".rb", ".sh",
    ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml",
    ".xml", ".sql", ".md", ".txt",
}

SUPPORTED_FILENAMES = {
    "Dockerfile",
    "Makefile",
}

IGNORED_DIRECTORIES = {
    # Version control
    ".git",

    # Python
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",

    # JavaScript
    "node_modules",

    # IDEs
    ".idea",
    ".vscode",

    # Build outputs
    "dist",
    "build",
    "target",
    "out",

    # Coverage / caches
    "coverage",
    ".coverage",
    ".cache",
}

PORTOFFLINE_IGNORE_FILE = ".portofflineignore"

IGNORE_COMMENT = "#"

def load_project(path):
    """Valida y devuelve la ruta absoluta de un proyecto."""
    project_path = Path(path).expanduser().resolve()

    if not project_path.exists():
        return None, f"Project not found: {path}"

    if not project_path.is_dir():
        return None, f"Not a directory: {path}"

    return project_path, None


def is_supported_file(path):
    """Comprueba si un archivo del proyecto es legible."""
    return (
        path.suffix.lower() in SUPPORTED_EXTENSIONS
        or path.name in SUPPORTED_FILENAMES
    )

def load_project_ignore(project_path):
    """Carga las reglas definidas en .portofflineignore."""
    ignore_file = project_path / PORTOFFLINE_IGNORE_FILE

    if not ignore_file.is_file():
        return []

    try:
        lines = ignore_file.read_text(
            encoding="utf-8"
        ).splitlines()
    except (OSError, UnicodeError):
        return []

    patterns = []

    for line in lines:
        pattern = line.strip()

        if not pattern:
            continue

        if pattern.startswith(IGNORE_COMMENT):
            continue

        # Normalizamos directorios: runtime/ -> runtime
        pattern = pattern.rstrip("/")

        if pattern:
            patterns.append(pattern)

    return patterns


def is_ignored_path(relative_path, ignore_patterns):
    """Comprueba si una ruta coincide con .portofflineignore."""

    path_string = relative_path.as_posix()

    for pattern in ignore_patterns:
        if (
            path_string == pattern
            or path_string.startswith(pattern + "/")
        ):
            return True

    return False

def get_project_files(project_path):
    """Obtiene archivos soportados respetando exclusiones."""

    import os

    files = []
    ignore_patterns = load_project_ignore(project_path)

    for root, dirs, filenames in os.walk(project_path):
        root_path = Path(root)

        filtered_dirs = []

        for directory in dirs:
            if directory in IGNORED_DIRECTORIES:
                continue

            directory_path = root_path / directory
            relative_directory = directory_path.relative_to(
                project_path
            )

            if is_ignored_path(
                relative_directory,
                ignore_patterns,
            ):
                continue

            filtered_dirs.append(directory)

        # Esto evita que os.walk entre en las carpetas excluidas.
        dirs[:] = filtered_dirs

        for filename in filenames:
            file_path = root_path / filename
            relative_path = file_path.relative_to(project_path)

            if is_ignored_path(
                relative_path,
                ignore_patterns,
            ):
                continue

            if not is_supported_file(file_path):
                continue

            files.append(relative_path)

    return sorted(files)


def resolve_project_file(project_path, filename):
    """Resuelve de forma segura un archivo dentro del proyecto."""
    file_path = (project_path / filename).resolve()

    try:
        file_path.relative_to(project_path)
    except ValueError:
        return None, "Access outside the active project is not allowed."

    if not file_path.exists():
        return None, f"File not found: {filename}"

    if not file_path.is_file():
        return None, f"Not a file: {filename}"

    if not is_supported_file(file_path):
        return None, f"Unsupported file type: {filename}"

    return file_path, None


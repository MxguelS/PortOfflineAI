"""Parsing multilenguaje mediante Tree-sitter."""

from pathlib import Path

from tree_sitter_language_pack import get_parser


LANGUAGE_BY_EXTENSION = {
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".go": "go",
    ".rs": "rust",
}


def get_language_for_file(file_path):
    """Obtiene el lenguaje Tree-sitter según la extensión."""

    extension = Path(file_path).suffix.lower()

    return LANGUAGE_BY_EXTENSION.get(extension)


def parse_code_file(file_path):
    """
    Parsea un archivo mediante Tree-sitter.

    Retorna el árbol, los bytes originales y un error opcional.
    """

    file_path = Path(file_path).resolve()

    if not file_path.is_file():
        return None, None, (
            f"File not found: {file_path}"
        )

    language = get_language_for_file(file_path)

    if language is None:
        return None, None, (
            f"Unsupported language: {file_path.suffix}"
        )

    try:
        source = file_path.read_bytes()
    except OSError as error:
        return None, None, (
            f"Could not read file: {error}"
        )

    try:
        parser = get_parser(language)
        tree = parser.parse(source)
    except Exception as error:
        return None, None, (
            f"Could not parse file: {error}"
        )

    return tree, source, None

def _node_text(node, source):
    """Obtiene el texto UTF-8 correspondiente a un nodo."""

    return source[
        node.start_byte:node.end_byte
    ].decode(
        "utf-8",
        errors="replace",
    )


def _get_node_name(node, source):
    """Obtiene el nombre declarado por un nodo."""

    name_node = node.child_by_field_name("name")

    if name_node is None:
        return None

    return _node_text(
        name_node,
        source,
    )


def _make_chunk(node, source, name, chunk_type):
    """Convierte un nodo Tree-sitter al formato de chunk."""

    content = _node_text(
        node,
        source,
    )

    return {
        "name": name,
        "type": chunk_type,
        "start_line": node.start_point.row + 1,
        "end_line": node.end_point.row + 1,
        "content": content,
        "size": len(
            content.encode("utf-8")
        ),
    }

def _extract_named_chunks(node, source, parent_name=None):
    """Extrae funciones, métodos y clases del AST."""

    chunks = []

    if node.type == "function_declaration":
        name = _get_node_name(
            node,
            source,
        )

        if name:
            chunks.append(
                _make_chunk(
                    node,
                    source,
                    name,
                    "function",
                )
            )

    elif node.type in {
        "method_definition",
        "method_declaration",
    }:
        name = _get_node_name(
            node,
            source,
        )

        if name:
            if parent_name:
                full_name = (
                    f"{parent_name}.{name}"
                )
            else:
                full_name = name

            chunks.append(
                _make_chunk(
                    node,
                    source,
                    full_name,
                    "method",
                )
            )

    elif node.type == "class_declaration":
        class_name = _get_node_name(
            node,
            source,
        )

        for child in node.named_children:
            chunks.extend(
                _extract_named_chunks(
                    child,
                    source,
                    parent_name=class_name,
                )
            )

        return chunks

    elif node.type == "variable_declarator":
        name = _get_node_name(
            node,
            source,
        )

        value_node = node.child_by_field_name(
            "value"
        )

        if (
            name
            and value_node is not None
            and value_node.type == "arrow_function"
        ):
            chunks.append(
                _make_chunk(
                    node,
                    source,
                    name,
                    "function",
                )
            )

    for child in node.named_children:
        chunks.extend(
            _extract_named_chunks(
                child,
                source,
                parent_name=parent_name,
            )
        )

    return chunks

def extract_code_chunks(file_path):
    """Extrae chunks estructurados usando Tree-sitter."""

    tree, source, error = parse_code_file(
        file_path
    )

    if error:
        return [], error

    chunks = _extract_named_chunks(
        tree.root_node,
        source,
    )

    return chunks, None
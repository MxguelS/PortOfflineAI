"""Utilidades para dividir archivos de código en fragmentos."""

import ast
from pathlib import Path
import re
import textwrap

STOP_WORDS = {
    "a",
    "al",
    "como",
    "con",
    "de",
    "del",
    "el",
    "en",
    "es",
    "este",
    "esta",
    "la",
    "las",
    "lo",
    "los",
    "para",
    "por",
    "que",
    "se",
    "un",
    "una",
    "y",
}

TERM_ALIASES = {
    "proyecto": "project",
    "proyectos": "project",
    "archivo": "file",
    "archivos": "file",
    "cargar": "load",
    "carga": "load",
    "descargar": "unload",
    "modo": "mode",
    "modos": "mode",
    "documento": "document",
    "documentos": "document",
    "contexto": "context",
    "respuesta": "response",
    "respuestas": "response",
}
MIN_CHUNK_SCORE = 3
MAX_SELECTED_CHUNKS = 6

def _get_source_lines(file_path):
    """Lee un archivo Python y devuelve su contenido y líneas."""

    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return None, None, str(error)

    return content, content.splitlines(), None


def _extract_chunk(lines, start_line, end_line):
    """Extrae un fragmento usando números de línea de AST."""

    return "\n".join(
        lines[start_line - 1:end_line]
    )

def _extract_imports(lines, tree):
    """Extrae los imports de nivel superior."""

    import_nodes = [
        node
        for node in tree.body
        if isinstance(
            node,
            (ast.Import, ast.ImportFrom),
        )
    ]

    if not import_nodes:
        return None

    start_line = min(
        node.lineno
        for node in import_nodes
    )

    end_line = max(
        getattr(node, "end_lineno", node.lineno)
        for node in import_nodes
    )

    content = _extract_chunk(
        lines,
        start_line,
        end_line,
    )

    return {
        "name": "imports",
        "type": "imports",
        "start_line": start_line,
        "end_line": end_line,
        "content": content,
        "size": len(content.encode("utf-8")),
    }

def extract_imported_names(content):
    """
    Extrae los nombres disponibles localmente
    a partir de los imports de un archivo Python.
    """

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    imported_names = set()

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imported_names.add(name)

        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_names.add(name)

    return imported_names

def extract_imports_by_module(content):
    """
    Agrupa los nombres importados según el módulo
    del que provienen.
    """

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {}

    imports_by_module = {}

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if not node.module:
                continue

            module_names = imports_by_module.setdefault(
                node.module,
                set(),
            )

            for alias in node.names:
                local_name = (
                    alias.asname or alias.name
                )

                module_names.add(local_name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name

                local_name = (
                    alias.asname
                    or alias.name.split(".")[0]
                )

                imports_by_module.setdefault(
                    module_name,
                    set(),
                ).add(local_name)

    return imports_by_module

def get_used_imports(chunk, imported_names):
    """
    Devuelve qué nombres importados aparecen
    realmente dentro de un chunk.
    """

    if chunk["type"] == "imports":
        return set()

    content = textwrap.dedent(
        chunk["content"]
    )

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    used_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    }

    return used_names & imported_names

def chunk_python_file(file_path):
    """Divide un archivo Python por clases, métodos y funciones."""

    file_path = Path(file_path).resolve()

    if not file_path.is_file():
        return [], f"File not found: {file_path}"

    content, lines, error = _get_source_lines(file_path)

    if error:
        return [], f"Could not read file: {error}"

    try:
        tree = ast.parse(
            content,
            filename=str(file_path),
        )
    except SyntaxError as error:
        return [], (
            f"Invalid Python syntax at "
            f"line {error.lineno}: {error.msg}"
        )

    chunks = []
    imports_chunk = _extract_imports(
        lines,
        tree,
    )

    if imports_chunk:
        chunks.append(imports_chunk)

    for node in tree.body:
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            chunks.append(
                _build_chunk(
                    lines=lines,
                    node=node,
                    name=node.name,
                    chunk_type="function",
                )
            )

        elif isinstance(node, ast.ClassDef):
            class_chunks = _chunk_class(
                lines,
                node,
            )

            chunks.extend(class_chunks)

    return chunks, None

def _chunk_class(lines, class_node):
    """Divide una clase Python en sus métodos."""

    chunks = []

    methods = [
        node
        for node in class_node.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
    ]

    # Si la clase no tiene métodos, guardamos la clase completa.
    if not methods:
        chunks.append(
            _build_chunk(
                lines=lines,
                node=class_node,
                name=class_node.name,
                chunk_type="class",
            )
        )

        return chunks

    for method in methods:
        chunks.append(
            _build_chunk(
                lines=lines,
                node=method,
                name=f"{class_node.name}.{method.name}",
                chunk_type="method",
            )
        )

    return chunks

def _build_chunk(
    lines,
    node,
    name,
    chunk_type,
):
    """Construye la representación de un fragmento."""

    start_line = node.lineno
    end_line = getattr(
        node,
        "end_lineno",
        node.lineno,
    )

    content = _extract_chunk(
        lines,
        start_line,
        end_line,
    )

    return {
        "name": name,
        "type": chunk_type,
        "start_line": start_line,
        "end_line": end_line,
        "content": content,
        "size": len(
            content.encode("utf-8")
        ),
    }

def _tokenize_text(text):
    """Normaliza texto en términos útiles para búsqueda."""

    text = text.lower().replace("_", " ")

    words = re.findall(
        r"[a-zA-Záéíóúñ][a-zA-Z0-9áéíóúñ]*",
        text,
    )

    normalized = set()

    for word in words:
        if word in STOP_WORDS:
            continue

        word = TERM_ALIASES.get(
            word,
            word,
        )

        normalized.add(word)

    return normalized

def _score_chunk(chunk, query_words):
    """Calcula la relevancia de un chunk para una consulta."""

    name_words = _tokenize_text(chunk["name"])
    content_words = _tokenize_text(chunk["content"])

    score = 0

    # Las coincidencias en el nombre son especialmente relevantes.
    score += len(query_words & name_words) * 5

    # Coincidencias dentro del código.
    score += len(query_words & content_words)

    # Los imports son baratos y muy útiles para entender relaciones.
    if chunk["type"] == "imports":
        score += 3

    return score

def select_relevant_chunks(
    chunks,
    query,
    max_size=8 * 1024,
):
    """
    Selecciona los chunks más relevantes para una consulta
    respetando un presupuesto máximo.
    """

    if not chunks:
        return []

    query_words = _tokenize_text(query)

    scored_chunks = []

    for chunk in chunks:
        score = _score_chunk(
            chunk,
            query_words,
        )

        scored_chunks.append(
            {
                "chunk": chunk,
                "score": score,
            }
        )

    scored_chunks.sort(
        key=lambda item: (
            item["score"],
            -item["chunk"]["size"],
        ),
        reverse=True,
    )

    selected = []
    total_size = 0

    for item in scored_chunks:
        chunk = item["chunk"]
        score = item["score"]

        # No llenamos contexto con fragmentos sin relación.
        if score <= 0:
            continue

        if total_size + chunk["size"] > max_size:
            continue

        selected.append(
            {
                **chunk,
                "score": score,
            }
        )

        total_size += chunk["size"]

    return selected

def select_global_chunks(
    file_chunks,
    query,
    max_size=8 * 1024,
):
    """
    Selecciona globalmente los chunks más relevantes
    entre múltiples archivos.
    """

    candidates = []

    for file_name, chunks in file_chunks:
        query_words = _tokenize_text(query)

        for chunk in chunks:
            score = _score_chunk(
                chunk,
                query_words,
            )

            if score <= 0:
                continue

            candidates.append(
                {
                    **chunk,
                    "file": file_name,
                    "score": score,
                }
            )

    candidates.sort(
        key=lambda item: (
            item["score"],
            -item["size"],
        ),
        reverse=True,
    )

    selected = []
    total_size = 0

    for chunk in candidates:
        if chunk["score"] < MIN_CHUNK_SCORE:
            continue

        if len(selected) >= MAX_SELECTED_CHUNKS:
            break

        if total_size + chunk["size"] > max_size:
            continue

        selected.append(chunk)
        total_size += chunk["size"]

    return selected

def find_dependency_chunks(
    chunks,
    imported_names,
):
    """
    Encuentra chunks que utilizan símbolos
    importados por el archivo.
    """

    dependency_chunks = []

    for chunk in chunks:
        used_imports = get_used_imports(
            chunk,
            imported_names,
        )

        if not used_imports:
            continue

        dependency_chunks.append(
            {
                **chunk,
                "dependencies": sorted(
                    used_imports
                ),
            }
        )

    return dependency_chunks

def find_chunks_using_symbols(
    chunks,
    symbols,
):
    """
    Encuentra chunks que utilizan cualquiera
    de los símbolos indicados.
    """

    matches = []

    for chunk in chunks:
        used_symbols = get_used_imports(
            chunk,
            symbols,
        )

        if not used_symbols:
            continue

        matches.append(
            {
                **chunk,
                "dependencies": sorted(
                    used_symbols
                ),
            }
        )

    return matches

def get_referenced_modules(
    query,
    file_names,
):
    """
    Detecta qué archivos del contexto son
    mencionados explícitamente en la consulta.
    """

    query_lower = query.lower()
    referenced = set()

    for file_name in file_names:
        path = Path(file_name)

        full_name = path.as_posix().lower()
        base_name = path.name.lower()
        stem = path.stem.lower()

        if (
            full_name in query_lower
            or base_name in query_lower
            or stem in query_lower
        ):
            referenced.add(
                path.with_suffix("")
                .as_posix()
                .replace("/", ".")
            )

    return referenced

def get_dependency_context(
    file_chunks,
    file_contents,
    query,
):
    """
    Encuentra chunks que demuestran relaciones
    entre módulos mencionados en la consulta.
    """

    file_names = [
        file_name
        for file_name, _ in file_chunks
    ]

    referenced_modules = get_referenced_modules(
        query,
        file_names,
    )

    dependency_context = []

    for file_name, chunks in file_chunks:
        content = file_contents.get(
            file_name,
            ""
        )

        if not content:
            continue

        imports_by_module = (
            extract_imports_by_module(content)
        )

        for module in referenced_modules:
            symbols = imports_by_module.get(
                module,
                set(),
            )

            if not symbols:
                continue

            matches = find_chunks_using_symbols(
                chunks,
                symbols,
            )

            for match in matches:
                dependency_context.append(
                    {
                        **match,
                        "file": file_name,
                        "dependency_module": module,
                    }
                )

    return dependency_context
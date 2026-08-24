"""Utilidades para dividir archivos de código en fragmentos."""

import ast
from pathlib import Path
import re
import textwrap

from src.tree_parser import (
    extract_code_chunks,
    get_language_for_file,
)

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

def _find_matching_brace(lines, start_index):
    """
    Busca la llave de cierre correspondiente a un bloque.

    Retorna el índice de la línea donde termina el bloque.
    """

    depth = 0
    found_opening = False

    for index in range(start_index, len(lines)):
        line = lines[index]

        for char in line:
            if char == "{":
                depth += 1
                found_opening = True

            elif char == "}":
                depth -= 1

                if found_opening and depth == 0:
                    return index

    return None

def _build_generic_chunk(
    name,
    chunk_type,
    lines,
    start_index,
    end_index,
):
    """Construye un chunk para código no-Python."""

    content = "\n".join(
        lines[start_index:end_index + 1]
    )

    return {
        "name": name,
        "type": chunk_type,
        "start_line": start_index + 1,
        "end_line": end_index + 1,
        "content": content,
        "size": len(
            content.encode("utf-8")
        ),
    }


def _chunk_java_file(lines):
    """
    Detecta clases y métodos Java de forma básica.

    Si no encuentra estructuras reconocibles,
    retorna una lista vacía para permitir fallback.
    """

    chunks = []

    class_pattern = re.compile(
        r"\b(?:class|interface|enum|record)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)"
    )

    method_pattern = re.compile(
        r"""
        ^\s*
        (?:
            public|protected|private|static|final|
            abstract|synchronized|native|strictfp|
            default
        )*
        \s*
        (?:<[^>]+>\s*)?
        [A-Za-z_][A-Za-z0-9_<>\[\],.? ]*
        \s+
        ([A-Za-z_][A-Za-z0-9_]*)
        \s*
        \([^;]*\)
        \s*
        (?:throws\s+[^{]+)?
        \{
        """,
        re.VERBOSE,
    )

    current_class = None

    for index, line in enumerate(lines):
        class_match = class_pattern.search(line)

        if class_match:
            current_class = class_match.group(1)

        method_match = method_pattern.search(line)

        if not method_match:
            continue

        method_name = method_match.group(1)

        if method_name in {
            "if",
            "for",
            "while",
            "switch",
            "catch",
        }:
            continue

        end_index = _find_matching_brace(
            lines,
            index,
        )

        if end_index is None:
            continue

        if current_class:
            chunk_name = (
                f"{current_class}.{method_name}"
            )
        else:
            chunk_name = method_name

        chunks.append(
            _build_generic_chunk(
                chunk_name,
                "method",
                lines,
                index,
                end_index,
            )
        )

    return chunks

def _chunk_javascript_file(lines):
    """
    Detecta funciones y métodos comunes en
    JavaScript y TypeScript.

    Si no encuentra estructuras reconocibles,
    retorna una lista vacía para permitir fallback.
    """

    chunks = []

    class_pattern = re.compile(
        r"\bclass\s+"
        r"([A-Za-z_$][A-Za-z0-9_$]*)"
    )

    function_pattern = re.compile(
        r"""
        ^\s*
        (?:export\s+)?
        (?:default\s+)?
        (?:async\s+)?
        function\s+
        ([A-Za-z_$][A-Za-z0-9_$]*)
        \s*
        (?:<[^>]+>)?
        \s*
        \([^)]*\)
        (?:\s*:\s*[^{]+)?
        \s*
        \{
        """,
        re.VERBOSE,
    )

    arrow_pattern = re.compile(
        r"""
        ^\s*
        (?:export\s+)?
        (?:const|let|var)
        \s+
        ([A-Za-z_$][A-Za-z0-9_$]*)
        \s*
        (?::[^=]+)?
        =
        \s*
        (?:async\s*)?
        (?:\([^)]*\)|[A-Za-z_$][A-Za-z0-9_$]*)
        \s*
        (?:\:\s*[^=]+)?
        =>
        \s*
        \{
        """,
        re.VERBOSE,
    )

    function_expression_pattern = re.compile(
        r"""
        ^\s*
        (?:export\s+)?
        (?:const|let|var)
        \s+
        ([A-Za-z_$][A-Za-z0-9_$]*)
        \s*
        (?::[^=]+)?
        =
        \s*
        (?:async\s+)?
        function
        (?:\s+[A-Za-z_$][A-Za-z0-9_$]*)?
        \s*
        \([^)]*\)
        (?:\s*:\s*[^{]+)?
        \s*
        \{
        """,
        re.VERBOSE,
    )

    method_pattern = re.compile(
        r"""
        ^\s*
        (?:
            public|private|protected|static|
            readonly|abstract|override
        )*
        \s*
        (?:async\s+)?
        ([A-Za-z_$][A-Za-z0-9_$]*)
        \s*
        (?:<[^>]+>)?
        \s*
        \([^)]*\)
        (?:\s*:\s*[^{]+)?
        \s*
        \{
        """,
        re.VERBOSE,
    )

    current_class = None
    class_end = -1

    for index, line in enumerate(lines):
        if (
            current_class is not None
            and index > class_end
        ):
            current_class = None
            class_end = -1

        class_match = class_pattern.search(line)

        if class_match:
            current_class = class_match.group(1)

            detected_end = _find_matching_brace(
                lines,
                index,
            )

            if detected_end is not None:
                class_end = detected_end

        match = function_pattern.search(line)
        chunk_type = "function"

        if not match:
            match = arrow_pattern.search(line)

        if not match:
            match = function_expression_pattern.search(
                line
            )

        if not match and current_class:
            match = method_pattern.search(line)

            if match:
                chunk_type = "method"

        if not match:
            continue

        name = match.group(1)

        if name in {
            "if",
            "for",
            "while",
            "switch",
            "catch",
            "constructor",
        }:
            continue

        end_index = _find_matching_brace(
            lines,
            index,
        )

        if end_index is None:
            continue

        if chunk_type == "method" and current_class:
            chunk_name = f"{current_class}.{name}"
        else:
            chunk_name = name

        chunks.append(
            _build_generic_chunk(
                chunk_name,
                chunk_type,
                lines,
                index,
                end_index,
            )
        )

    return chunks

def chunk_generic_code_file(
    file_path,
    max_chunk_size=2048,
):
    """
    Divide código no-Python en fragmentos genéricos.

    Intenta respetar líneas completas y evita
    enviar archivos enteros al contexto.
    """

    file_path = Path(file_path).resolve()

    if not file_path.is_file():
        return [], f"File not found: {file_path}"

    try:
        content = file_path.read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeDecodeError) as error:
        return [], f"Could not read file: {error}"

    lines = content.splitlines()

    if not lines:
        return [], None

    extension = file_path.suffix.lower()

    semantic_chunks = []

    if extension == ".java":
        semantic_chunks = _chunk_java_file(
            lines
        )

    elif extension in {
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
    }:
        semantic_chunks = _chunk_javascript_file(
            lines
        )

    if semantic_chunks:
        return semantic_chunks, None

    chunks = []
    current_lines = []
    current_size = 0
    start_line = 1

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        line_with_newline = line + "\n"
        line_size = len(
            line_with_newline.encode("utf-8")
        )

        if (
            current_lines
            and current_size + line_size
            > max_chunk_size
        ):
            chunk_content = "\n".join(
                current_lines
            )

            chunks.append(
                {
                    "name": (
                        f"lines_{start_line}_"
                        f"{line_number - 1}"
                    ),
                    "type": "code",
                    "start_line": start_line,
                    "end_line": line_number - 1,
                    "content": chunk_content,
                    "size": len(
                        chunk_content.encode(
                            "utf-8"
                        )
                    ),
                }
            )

            current_lines = []
            current_size = 0
            start_line = line_number

        current_lines.append(line)
        current_size += line_size

    if current_lines:
        chunk_content = "\n".join(
            current_lines
        )

        chunks.append(
            {
                "name": (
                    f"lines_{start_line}_"
                    f"{len(lines)}"
                ),
                "type": "code",
                "start_line": start_line,
                "end_line": len(lines),
                "content": chunk_content,
                "size": len(
                    chunk_content.encode(
                        "utf-8"
                    )
                ),
            }
        )

    return chunks, None

def _tokenize_text(text):
    """Convierte texto y nombres de código en tokens."""

    if not text:
        return set()

    normalized = re.sub(
        r"([a-z0-9])([A-Z])",
        r"\1 \2",
        text,
    )

    normalized = re.sub(
        r"[_\-.\\/]+",
        " ",
        normalized,
    )

    words = re.findall(
        r"[A-Za-zÀ-ÿ0-9]+",
        normalized.lower(),
    )

    tokens = set(words)

    for word in words:
        if len(word) > 4:
            if word.endswith("ar"):
                tokens.add(word[:-2])

            elif word.endswith("er"):
                tokens.add(word[:-2])

            elif word.endswith("ir"):
                tokens.add(word[:-2])

    return tokens

def _words_match(left, right):
    """Compara tokens exactos o con una raíz común."""

    if left == right:
        return True

    if len(left) < 5 or len(right) < 5:
        return False

    # Coincidencia por prefijo directo.
    if (
        left.startswith(right)
        or right.startswith(left)
    ):
        return True

    # Coincidencia por raíz común.
    common_length = 0

    for left_char, right_char in zip(left, right):
        if left_char != right_char:
            break

        common_length += 1

    minimum_length = min(
        len(left),
        len(right),
    )

    return (
        common_length >= 4
        and common_length >= minimum_length - 1
    )

def _score_chunk(chunk, query_words):
    """Calcula la relevancia de un chunk para una consulta."""

    name_words = _tokenize_text(chunk["name"])
    content_words = _tokenize_text(chunk["content"])

    score = 0

    # Coincidencias exactas en el nombre.
    exact_name_matches = query_words & name_words
    score += len(exact_name_matches) * 5

    # Coincidencias aproximadas en el nombre.
    for query_word in query_words:
        if query_word in exact_name_matches:
            continue

        if any(
            _words_match(query_word, name_word)
            for name_word in name_words
        ):
            score += 3

    # Coincidencias exactas dentro del código.
    exact_content_matches = (
        query_words & content_words
    )
    score += len(exact_content_matches)

    # Coincidencias aproximadas dentro del código.
    for query_word in query_words:
        if query_word in exact_content_matches:
            continue

        if any(
            _words_match(query_word, content_word)
            for content_word in content_words
        ):
            score += 1

    # Los imports son baratos y útiles para entender relaciones.
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
            file_words = _tokenize_text(
                file_name
            )

            score += len(
                query_words & file_words
            ) * 5

            if score <= 0:
                continue

            

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
        if Path(file_name).suffix.lower() != ".py":
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

PYTHON_EXTENSIONS = {
    ".py",
}

GENERIC_CODE_EXTENSIONS = {
    ".java",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".cs",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".go",
    ".rs",
    ".php",
    ".kt",
    ".kts",
    ".swift",
    ".rb",
    ".sh",
    ".fish",
}


def chunk_code_file(file_path):
    """
    Selecciona el chunker apropiado según
    el lenguaje del archivo.

    Python utiliza el AST nativo.
    Los lenguajes compatibles utilizan Tree-sitter.
    Si Tree-sitter no puede generar chunks,
    se utiliza el chunker genérico como fallback.
    """

    file_path = Path(file_path)
    extension = file_path.suffix.lower()

    if extension in PYTHON_EXTENSIONS:
        return chunk_python_file(file_path)

    tree_sitter_language = get_language_for_file(
        file_path
    )

    if tree_sitter_language is not None:
        chunks, error = extract_code_chunks(
            file_path
        )

        if chunks:
            return chunks, None

        if error is None:
            return chunk_generic_code_file(
                file_path
            )

    if extension in GENERIC_CODE_EXTENSIONS:
        return chunk_generic_code_file(
            file_path
        )

    return [], (
        f"Unsupported code file: "
        f"{file_path.name}"
    )
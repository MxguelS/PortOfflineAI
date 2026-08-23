# PortOfflineAI

PortOfflineAI es un proyecto experimental cuyo objetivo es crear un **asistente de IA portátil y completamente offline**, capaz de ejecutarse utilizando los recursos de la computadora sin depender de APIs o servicios de IA en la nube.

> **Versión actual:** v0.1.0 — Prototipo inicial

## Estado actual

La versión `v0.1.0` demuestra el funcionamiento básico del concepto:

* Inferencia de IA completamente local.
* Funcionamiento sin conexión a Internet.
* Ejecución mediante CPU.
* Conversación desde la terminal.
* Configuración mediante `config.json`.
* Inicio mediante `open.sh`.

Actualmente utiliza:

* **Python 3**
* **llama.cpp**
* **Qwen3-4B Q4_K_M**
* **GGUF**

## Estructura

```text
PortOfflineAI/
├── README.md
├── open.sh
├── src/
│   └── main.py
├── config/
│   └── config.json
├── models/
└── runtime/
```

Los modelos GGUF y `llama.cpp` no se almacenan en el repositorio debido a su tamaño.

## Preparación

### 1. Clonar llama.cpp

```bash
git clone https://github.com/ggml-org/llama.cpp.git runtime/llama.cpp
```

### 2. Compilar llama-cli

```bash
cd runtime/llama.cpp
cmake -B build
cmake --build build --config Release -j --target llama-cli
cd ../../..
```

### 3. Agregar el modelo

Colocar:

```text
Qwen3-4B-Q4_K_M.gguf
```

dentro de:

```text
models/
```

La ruta del modelo puede modificarse desde `config/config.json`.

## Ejecución

Dar permisos al launcher:

```bash
chmod +x open.sh
```

Ejecutar:

```bash
./open.sh
```

Una vez cargado el modelo, PortOfflineAI permitirá conversar directamente desde la terminal.

## Limitaciones

La versión `v0.1.0` todavía no incluye RAG, detección de hardware, selección automática de modelos, interfaz gráfica, aceleración automática por GPU ni distribución portable para Windows.

Las respuestas del modelo pueden contener información incorrecta.

## Objetivo

El proyecto evolucionará progresivamente hacia un asistente capaz de ejecutarse desde un **SSD o USB**, seleccionar modelos según el hardware disponible y consultar documentación local mediante RAG.

También se contempla una futura versión **Lite**, diseñada para USB y computadoras de bajos recursos.

## Licencia

MIT

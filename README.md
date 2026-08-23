# PortOfflineAI

PortOfflineAI es un proyecto experimental para construir un asistente de inteligencia artificial portátil, local y completamente offline.

La idea es poder almacenar el agente, su runtime, los modelos y eventualmente su base de conocimiento en una unidad portátil, ejecutándolo con los recursos de la computadora disponible sin depender de APIs externas ni conexión a Internet.

> Estado del proyecto: prototipo en desarrollo.

## Objetivo

PortOfflineAI busca convertirse en una herramienta de asistencia técnica y programación que pueda utilizarse en lugares con conectividad limitada o inexistente.

El flujo final planteado es sencillo:

```text
Unidad portátil
      ↓
PortOfflineAI
      ↓
Runtime local
      ↓
Modelo LLM
      ↓
Respuesta offline
```

El proyecto se está desarrollando de forma incremental: primero hacer funcionar correctamente la inferencia local, después construir una experiencia propia alrededor del modelo y finalmente incorporar conocimiento técnico portátil y selección de hardware/modelos.

## Estado actual — v0.2.0

La versión estable actual es **v0.2.0**.

Actualmente PortOfflineAI puede:

- Ejecutar un LLM completamente offline.
- Utilizar `llama.cpp` como runtime local.
- Ejecutar el modelo mediante `llama-server` y una API HTTP exclusivamente local.
- Mantener historial durante una conversación.
- Responder preguntas generales y técnicas.
- Generar y explicar código.
- Renderizar Markdown directamente en la terminal.
- Funcionar únicamente con CPU, sin requerir una GPU.
- Iniciarse y cerrarse mediante un launcher propio.
- Mostrar métricas básicas de generación.

La CLI incluye actualmente:

```text
/help      Show available commands
/clear     Clear conversation history
/status    Show PortOfflineAI status
/exit      Close PortOfflineAI
```

Durante las pruebas de v0.2.0, **Qwen3-4B Q4_K_M** generó un programa Java completo para gestionar una lista de tareas. El código generado fue compilado posteriormente con `javac` y ejecutado correctamente, incluyendo creación, listado y eliminación de tareas y validación de una selección inválida.

## Modelo utilizado

El modelo utilizado actualmente para desarrollo y pruebas es:

```text
Qwen3-4B Q4_K_M
Formato: GGUF
Runtime: llama.cpp
Backend probado: CPU
```

Los modelos no se almacenan en el repositorio debido a su tamaño. Cada instalación debe colocar el archivo GGUF correspondiente dentro del directorio local de modelos.

## Estructura del proyecto

```text
PortOfflineAI/
├── config/
│   └── config.json
├── models/
│   └── <modelo>.gguf
├── runtime/
│   └── llama.cpp/
├── src/
│   └── main.py
├── open.sh
├── requeriments.txt
└── README.md
```

Los modelos, entornos virtuales y artefactos pesados de compilación no forman parte del código fuente versionado.

## Ejecución

Con el entorno y el modelo preparados, PortOfflineAI se inicia desde la raíz del proyecto con:

```bash
./open.sh
```

El launcher inicia el servidor local, espera a que el modelo esté disponible y abre la interfaz de conversación en la terminal.

Todo el tráfico utilizado para la inferencia permanece en la máquina local.

## Rendimiento de referencia

Las primeras pruebas se realizaron con Qwen3-4B Q4_K_M ejecutándose únicamente mediante CPU.

En el equipo de desarrollo se observaron aproximadamente **7 tokens por segundo** durante generaciones sostenidas. Este valor es únicamente una referencia y variará considerablemente según CPU, RAM, configuración, modelo y cuantización.

## Versiones

### v0.1.0 — Primer prototipo

Primera prueba funcional de PortOfflineAI. El objetivo era demostrar que un modelo GGUF podía almacenarse localmente y responder completamente offline mediante `llama.cpp`.

### v0.2.0 — CLI y servidor local

PortOfflineAI dejó de ser solamente una ejecución directa del modelo y comenzó a incorporar su propia capa de aplicación:

- API local con `llama-server`.
- CLI propia con Rich.
- Historial de conversación.
- Comandos internos.
- Renderizado Markdown.
- Optimizaciones para ejecución local.
- Métricas de generación.

## En desarrollo — v0.3.0

La siguiente versión está enfocada en **Local Knowledge**.

El objetivo es permitir que PortOfflineAI consulte documentación almacenada junto al proyecto, comenzando con archivos de texto y Markdown.

Plan inicial:

```text
knowledge/
├── manual.txt
├── notas.md
└── documentacion.txt
```

Funciones previstas para esta etapa:

- Descubrir documentos locales.
- Listar documentos disponibles con `/docs`.
- Cargar un documento para utilizarlo como contexto.
- Descargar el documento activo de la conversación.
- Mostrar el documento activo en `/status`.
- Limitar el tamaño del contexto cargado.

PDF, embeddings y RAG vectorial se consideran etapas posteriores y no forman parte del alcance inicial de v0.3.0.

## Visión

A largo plazo, PortOfflineAI busca poder transportarse en un SSD externo o, mediante una edición ligera, en una memoria USB.

Una versión futura podría detectar automáticamente los recursos de la computadora anfitriona y seleccionar un modelo apropiado según la RAM, CPU y GPU disponibles.

```text
Conectar unidad
      ↓
Iniciar PortOfflineAI
      ↓
Detectar hardware
      ↓
Seleccionar modelo
      ↓
Cargar conocimiento local
      ↓
Asistencia técnica offline
```

El objetivo no es reemplazar servicios de IA en la nube, sino disponer de una alternativa autónoma y portátil para situaciones donde Internet no esté disponible o no sea conveniente.

## Licencia

El proyecto se encuentra en desarrollo. Antes de distribuir modelos o binarios junto con PortOfflineAI, deben revisarse y respetarse las licencias correspondientes de cada componente utilizado.
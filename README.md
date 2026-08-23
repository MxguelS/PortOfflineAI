# PortOfflineAI

**PortOfflineAI** es un asistente de inteligencia artificial portátil diseñado para funcionar completamente offline utilizando modelos GGUF locales y `llama.cpp`.

La idea es simple: conectar un USB o SSD externo, iniciar PortOfflineAI y tener acceso a una IA privada sin depender de Internet ni servicios en la nube.

![Demostración de PortOfflineAI](assets/demo.gif)

## Características

- Ejecución de IA completamente offline
- Modelos GGUF locales
- Ejecución mediante CPU
- API local compatible con OpenAI
- Interfaz moderna en terminal
- Renderizado de Markdown
- Historial de conversación
- Métricas de generación
- Conocimiento mediante documentos locales
- Sin APIs ni servicios en la nube

## Conocimiento local

PortOfflineAI puede utilizar documentos `.txt` y `.md` como contexto adicional para responder preguntas.

```text
/docs
/read <archivo>
/unload
/status
```

Los documentos se almacenan en:

```text
knowledge/
```

Actualmente cada documento puede tener un tamaño máximo de **32 KB**.

## Comandos

| Comando | Descripción |
|---|---|
| `/help` | Mostrar los comandos disponibles |
| `/clear` | Limpiar el historial de conversación |
| `/status` | Mostrar el estado del sistema |
| `/docs` | Mostrar los documentos disponibles |
| `/read <archivo>` | Cargar un documento local |
| `/unload` | Descargar el documento activo |
| `/exit` | Cerrar PortOfflineAI |

## Estructura

```text
PortOfflineAI/
├── config/
├── knowledge/
├── models/
├── runtime/
│   └── llama.cpp/
├── src/
│   └── main.py
├── open.sh
└── README.md
```

## Modelo actual

El desarrollo y las pruebas se realizan actualmente con:

```text
Qwen3-4B-Q4_K_M.gguf
```

El modelo se ejecuta localmente mediante `llama-server`.

## Ejecución

Instala las dependencias de Python:

```bash
pip install -r requeriments.txt
```

Coloca un modelo GGUF compatible dentro de `models/` y configura su ruta en `config/config.json`.

Luego ejecuta:

```bash
chmod +x open.sh
./open.sh
```

## Estado actual

**v0.3.0 — Conocimiento local**

PortOfflineAI puede ejecutar un LLM offline, mantener conversaciones, generar código, exponer una API local y responder preguntas utilizando documentos cargados desde el dispositivo.

Durante las pruebas, Qwen3-4B generó un gestor de tareas completo en Java que posteriormente fue compilado y ejecutado correctamente con `javac`.

## Próximamente

- Soporte para PDF
- Múltiples documentos
- Chunking y RAG
- Detección automática de hardware
- Aceleración mediante GPU
- Mayor portabilidad entre equipos

## Licencia

Proyecto actualmente en desarrollo.
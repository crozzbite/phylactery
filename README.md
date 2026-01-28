# 💀 Phylactery

> **"Infraestructura como Código para la Inteligencia."**
> La placa base donde conectas tus agentes para hacerlos productivos.

Phylactery es una API agnóstica de agentes diseñada bajo la filosofía **"Bones + Brain"**. Permite definir, desplegar y consumir agentes de IA utilizando un flujo de trabajo **GitOps** puro: solo editas archivos Markdown, y la API se encarga del resto.

---

## ⚡ Features

*   **GitOps Native**: Define tus agentes en `.agent/agents/*.md`. Cargas automáticas al iniciar.
*   **Multi-Provider Brain**: Elige el cerebro adecuado para cada tarea:
    *   🟢 **Ollama** (Local/Gratis) - Para desarrollo y privacidad.
    *   🔵 **OpenAI** (GPT-4) - Para razonamiento complejo.
    *   🟠 **Gemini** (Google) - Para ventanas de contexto masivas.
*   **Provider Override**: Define un proveedor global en `.env` o específico para cada agente en su frontmatter.
*   **Docker Ready**: Despliegue en un comando con `docker-compose`.
*   **Type-Safe**: Escrito en Python 3.13 con FastAPI, validado con `mypy --strict` y `ruff`.

---

## 🚀 Quick Start

### 1. Requisitos
*   Docker & Docker Compose
*   (Opcional) Python 3.13+ y `uv` para desarrollo local.

### 2. Ejecutar con Docker (Recomendado)

```bash
# 1. Clona el repo
git clone https://github.com/crozzbite/phylactery.git
cd phylactery

# 2. Configura tus llaves (Ollama funciona sin keys)
cp .env.example .env
# Edita .env si vas a usar OpenAI/Gemini

# 3. Levanta la magia
docker-compose up --build
```

La API estará disponible en `http://localhost:8000`.

### 3. Crear tu Primer Agente

Crea un archivo en `.agent/agents/asistente.md`:

```markdown
---
role: Asistente Personal
ai_provider: ollama  # Opcional: openai, gemini
---

Eres un asistente sarcástico que responde todo con metáforas de calaveras.
```

¡Listo! Tu agente ya está vivo.

### 4. Hablar con el Agente

```bash
curl -X POST "http://localhost:8000/chat/asistente" \
     -H "Content-Type: application/json" \
     -d '{"message": "Hola, ¿quién eres?"}'
```

---

## 🧠 Arquitectura

### Estructura del Proyecto

```text
phylactery/
├── .agent/              # TU CONOCIMIENTO (The Brain)
│   ├── agents/          # Definiciones de Agentes (.md)
│   └── skills/          # Habilidades Reutilizables (.md)
├── src/                 # EL CÓDIGO (The Bones)
│   ├── app/
│   │   ├── core/        # Lógica del Engine (LangGraph)
│   │   ├── main.py      # FastAPI Entrypoint
│   │   └── models.py    # Pydantic Models
├── Dockerfile           # Receta de construcción
└── docker-compose.yml   # Orquestación (API + Ollama)
```

### Filosofía de Diseño

1.  **Tangibilidad**: Los agentes son archivos. Si borras el archivo, muere el agente.
2.  **Transparencia**: Todo el prompt y la configuración están a la vista.
3.  **Independencia**: No te casamos con un proveedor. Cambia de OpenAI a Ollama en una línea.

---

## 🛠️ Desarrollo Local

Si prefieres correrlo sin Docker:

```bash
# Instalar uv (si no lo tienes)
pip install uv

# Instalar dependencias
uv sync

# Correr servidor
uv run uvicorn src.app.main:app --reload
```

---

## 📜 Orígenes y Conocimiento
Phylactery es un proyecto de **SkullRender**, inspirado en la filosofía de **Gentleman-Programming**. Originalmente concebido para potenciar AI Agents con habilidades específicas y patrones de arquitectura limpia.

### 🛡️ Guía Rápida del Lich
*   **Añadir Espíritus**: Coloca archivos `.md` en `.agent/agents/`.
*   **Invocación**: Usa `{@nombre_agente}` para llamar a un agente.
*   **Límite de Almas**: Se recomienda mantener entre 3 y 5 agentes activos simultáneamente para un rendimiento óptimo.

Para un catálogo detallado de agentes y habilidades, consulta: [AGENTS.md](file:///c:/Users/HP/.gemini/antigravity/playground/phylactery/AGENTS.md)

---

---

## 💻 CLI (Herramienta de Infección)

Phylactery incluye una herramienta de línea de comandos para interactuar con tus agentes sin salir de la terminal.

### Instalación
Si estás en el entorno de desarrollo:
```bash
uv run phylactery --help
```

### Comandos
1.  **Listar Agentes**:
    ```bash
    uv run phylactery list
    ```
2.  **Chatear (Default: Presentador)**:
    ```bash
    uv run phylactery chat
    ```
    *(Inicia una sesión con el agente orquestador `phylactery`)*

3.  **Chatear con un Agente específico**:
    ```bash
    uv run phylactery chat python_architect
    ```
    *(Abre una sesión interactiva con el agente)*


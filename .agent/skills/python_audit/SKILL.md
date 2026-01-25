---
name: python_audit
description: Auditoría de calidad, arquitectura y performance para proyectos Python (Based on FastAPI).
metadata:
  version: 1.0.0
  author: SkullRender AI
  tags: [python, fastapi, quality, security]
---

# SKILL: Python Project Audit (SkullRender Standard)

> [!IMPORTANT]
> **Filosofía**: "Bones + Brain". Estructura sólida, tipado estricto y cero deuda técnica.
> Inspirado en la arquitectura de **FastAPI**, este skill define las reglas innegociables para proyectos Python en SkullRender.

## When to Use
*   Cuando se audita un nuevo repositorio Python.
*   En el pipeline de CI/CD (Pre-commit).
*   Al iniciar un refactor de un servicio legacy.

## Critical Patterns (The "Must Haves")

### 1. Los Huesos (Infraestructura)
*   **Package Management**: Uso obligatorio de **`uv`** (o `pdm` como fallback). `pip` directo está prohibido.
*   **Configuración Única**: Todo en `pyproject.toml`.
*   **Hooks**: `.pre-commit-config.yaml` presente y activo.

### 2. El Cerebro (Tipado)
*   **Strict Mode**: `mypy --strict` configurado en CI.
*   **No Any**: El uso de `Any` debe ser explícitamente ignorado con `# type: ignore[misc]` y justificado.

### 3. Músculos (Testing)
*   **Coverage**: >95% en lógica de negocio.
*   **Pytest**: Único runner permitido.
*   **Modern Assertions**: Preferir `dirty-equals` sobre validaciones manuales de diccionarios.

## Anti-Patterns (The "Never Do's")

*   ❌ Usar `requirements.txt` sin lockfile (usar `uv.lock`).
*   ❌ Mezclar lógica de negocio en controladores (`routers`).
*   ❌ "Pokemon Exception Handling" (`except Exception: pass`).
*   ❌ Configuración dispersa (`setup.cfg`, `.flake8` separados).

## Code Examples

### Good: Estructura Modular
```text
project_root/
├── pyproject.toml
├── uv.lock
├── src/
│   └── my_app/
│       ├── __init__.py
│       ├── main.py
│       └── routers/
└── tests/
```

### Good: Pyproject.toml Configuration
```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.mypy]
strict = true
ignore_missing_imports = true
```

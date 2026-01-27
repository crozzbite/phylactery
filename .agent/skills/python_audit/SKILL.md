---
name: python-audit
description: >
  Auditoría de calidad, arquitectura y performance para proyectos Python.
  Trigger: Cuando se audita un repositorio Python, se inicia un refactor o se configura CI/CD.
metadata:
  version: 1.1.0
  author: SkullRender (Antigravity)
---

## When to Use
Load this skill when:
- Auditing a new Python repository (FastAPI/General).
- Configuring CI/CD pipelines or pre-commit hooks.
- Starting a refactor of legacy services.

## Critical Patterns

### 1. The Bones (Infraestructura)
"Bones + Brain" - A solid structure is non-negotiable.

| Component | Standard | Why |
|-----------|----------|-----|
| Package Manager | `uv` | Modern, fast, and reliable lockfiles. |
| Configuration | `pyproject.toml` | Single source of truth for tools. |
| MCP Servers | No `print()` | Avoid breaking the protocol; use logging. |

### 2. The Brain (Type Safety)
Strict typing ensures long-term maintainability.

| Pattern | Rule |
|---------|------|
| Typing | `mypy --strict` mandatory. |
| `Any` | Prohibited unless justified with `# type: ignore`. |
| Coverage | >95% in business logic. |

## Code Examples

### Example: Standard pyproject.toml
```toml
[tool.mypy]
strict = true
ignore_missing_imports = true

[tool.ruff]
line-length = 88
target-version = "py311"
```

## Anti-Patterns

### Don't: Manual Dependencies
Why: Manual `requirements.txt` are brittle. Use `uv.lock`.
```text
# ❌ Using requirements.txt without a lockfile
```

### Don't: Pokemon Exception Handling
Why: Masking errors makes debugging impossible.
```python
# ❌ except Exception: pass
```

## Quick Reference
- **Runner**: `pytest` only.
- **MCP Logging**: Log to `stderr`.
- **Formatting**: `ruff` is the standard.

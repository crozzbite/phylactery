---
name: github-pr
description: Rules for Git, Pull Requests, and Conventional Commits.
metadata:
  version: 1.0.0
  author: SkullRender AI
  tags: [git, github, collaboration]
---

# SKILL: Git & Pull Requests

## Critical Patterns

### 1. Conventional Commits
Todos los mensajes de commit deben seguir el estándar:
*   `feat: add user login` (Nueva funcionalidad)
*   `fix: resolve crash on startup` (Bug fix)
*   `docs: update readme` (Documentación)
*   `refactor: simplify auth logic` (Cambios de código sin features nuevas)
*   `test: add unit tests` (Tests)

### 2. Pull Requests
*   **Título Descriptivo**: Igual que el commit (`feat: ...`).
*   **Descripción**: Debe explicar *qué* cambió y *por qué*.
*   **Atomicidad**: Un PR debe resolver UNA sola cosa. No mezclar refactors con features.

### 3. Git History
*   **No Merge Commits**: Usar `rebase` para mantener un historial lineal antes de mergear.
*   **Squash**: Si hay muchos commits de "wip" o "fix typo", hacer squash antes del merge final.

## Anti-Patterns

*   ❌ Commits tipo "wip", "fix", "point".
*   ❌ PRs gigantes (+500 líneas) que tocan múltiples dominios.
*   ❌ Subir archivos secretos (`.env`) o carpetas de build (`dist/`, `__pycache__`).

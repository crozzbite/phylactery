<!--
╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│   GENTLEMAN GUARDIAN ANGEL :: AGENTS.md                                      │
│                                                                              │
│   This file aggregates the active rules and agents for the project.          │
│   It is used by the pre-commit hook to audit changes.                        │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
-->

# Active Agents

- [Python Architect](.agent/agents/python_architect.md)
  - **Scope**: `**/*.py`, `pyproject.toml`
  - **Skills**:
    - [Python Audit](.agent/skills/python_audit/SKILL.md)
    - [Git Standards](.agent/skills/github-pr/SKILL.md)

# Installed Skills Reference
*   [Angular Moderno](.agent/skills/angular/SKILL.md)
*   [TypeScript Strict](.agent/skills/typescript/SKILL.md)
*   [Git & PRs](.agent/skills/github-pr/SKILL.md)

# Global Rules

1.  **Bones + Brain**: Structure first, logic second.
2.  **No Broken Windows**: Zero linting errors allowed.
3.  **Documentation**: All public APIs must be documented.

# Protocol for New Tools

> [!TIP]
> **"Don't Reinvent the Wheel"**
> When a new tool is introduced to the project:
> 1.  **Check Repository**: Look into [`Gentleman-Skills/curated`](https://github.com/Gentleman-Programming/Gentleman-Skills/tree/main/curated) first.
> 2.  **Import**: If it exists, copy the `SKILL.md` to `.agent/skills/<tool>/`.
> 3.  **Create**: Only creation from scratch if it's not in the official repo.

---
name: github-pr
description: >
  Rules for Git, Pull Requests, and Conventional Commits.
  Trigger: When creating commits, opening PRs, or managing git history.
metadata:
  version: 1.1.0
  author: SkullRender (Antigravity)
---

## When to Use
Load this skill when:
- Committing code to a repository.
- Opening a Pull Request on GitHub.
- Reorganizing git history (rebase/squash).

## Critical Patterns

### 1. Conventional Commits
All commit messages MUST follow the spec.

| Type | Example | Usage |
|------|---------|-------|
| `feat` | `feat: add user login` | New functionality. |
| `fix` | `fix: resolve crash` | Bug fix. |
| `docs` | `docs: update readme` | Documentation only. |
| `refactor`| `refactor: simplify auth` | Code change (no features). |

### 2. PR Integrity
Atomic changes for clean reviews.

| Rule | Requirement |
|------|-------------|
| Title | Matches commit (`feat: ...`). |
| Description | Explains WHAT and WHY. |
| Atomic | One PR = One Task/Fix. |

## Code Examples

### Example: Proper Commit Message
```bash
feat(auth): implement OIDC provider for skullrender
```

## Anti-Patterns

### Don't: Generic Commits
Why: Makes history impossible to read and automate.
```bash
# ❌ wip, point, fix, update
```

### Don't: Giant PRs (+500 lines)
Why: Impossible to review properly; increases risk of bugs.
```text
# ❌ Overly complex PR touching 10+ files and 5 domains
```

## Quick Reference
- **History**: Use `rebase` for linear history.
- **Cleanup**: `squash` WIP commits before merge.
- **Ignored**: Never upload `.env` or `__pycache__`.

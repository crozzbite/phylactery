---
name: guardian-angel
description: >
  Core rules of the Gentleman Guardian Angel (GGA) for SkullRender.
  Trigger: When auditing code for architecture, naming, and technical standards.
metadata:
  version: 1.1.0
  author: Gentleman-Programming & SkullRender (Antigravity)
---

## When to Use
Load this skill when:
- Reviewing Merge Requests (MR) or code changes.
- Setting up a new Angular project.
- Auditing existing legacy code for cleanup.

## Critical Patterns

### 1. The Scope Rule
Code must live exactly where its usage dictates. "Scope determines structure".

| Usage | Placement |
|-------|-----------|
| Used by 1 feature | `features/[feature]/components/` |
| Used by 2+ features | `shared/` |
| App-wide singletons | `core/` |

### 2. Radical Naming
No redundant suffixes. The structure Provides the context.

| Entity | ❌ Incorrect | ✅ Correct |
|--------|-------------|------------|
| Service | `user.service.ts` | `user.ts` |
| Component | `login.component.ts` | `login.ts` |

## Code Examples

### Example: Clean Feature Structure
```typescript
// src/app/features/user/services/user.ts
@Injectable({ providedIn: 'root' })
export class UserService { ... }
```

## Anti-Patterns

### Don't: Redundant Suffixes
Why: It's redundant. The folder (services, components) already provides the context.
```typescript
// ❌ user.service.ts - REJECTED
```

### Don't: Manual State Subscription
Why: Prefer Signals (`toSignal`) or `AsyncPipe` to avoid memory leaks.
```typescript
// ❌ this.service.get().subscribe() - REJECTED
```

## Quick Reference
- **Signals**: Native state management only.
- **Standalone**: Required for every component.
- **Response**: Must start with `STATUS: PASSED` or `STATUS: FAILED`.

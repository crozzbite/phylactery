---
name: typescript
description: >
  Strict TypeScript rules for SkullRender.
  Trigger: When writing TypeScript code, defining interfaces, or managing types.
metadata:
  version: 1.1.0
  author: SkullRender (Antigravity)
---

## When to Use
Load this skill when:
- Writing new TypeScript code.
- Defining models, interfaces, or types.
- Cleaning up untyped or loosely typed code.

## Critical Patterns

### 1. Strict Typing
"If it compiles, it must be correct".

| Pattern | Rule | Why |
|---------|------|-----|
| `any` | FORBIDDEN | Use `unknown` and type guards instead. |
| Returns | Explicitly declare | Improves readability and prevents logic errors. |
| Null Checks | Strict | Force the handling of `null/undefined`. |

### 2. Data Structures
Prefer modern, lean type definitions.

| Use Case | Pattern |
|----------|---------|
| Enums | ❌ Prohibited. Use `const assertions` or `Union Types`. |
| Immutability| Use `readonly` for arrays and object properties. |
| Validation | Use `Zod` for runtime validation. |

## Code Examples

### Example: Proper Union Types
```typescript
type Role = 'Admin' | 'User';

const ROLES = {
  ADMIN: 'Admin',
  USER: 'User'
} as const;
```

## Anti-Patterns

### Don't: Non-Null Assertions (`!`)
Why: It lies to the compiler and causes runtime crashes.
```typescript
// ❌ const user = users.find(u => u.id === id)!;
```

### Don't: Interface Prefixes
Why: Redundant and outdated.
```typescript
// ❌ interface IUser { ... }
```

## Quick Reference
- **No Enums**: Only Union Types or Const Assertions.
- **Strict**: `strict: true` in `tsconfig.json`.
- **Naming**: Use PascalCase for types/interfaces.

---
name: typescript
description: Strict TypeScript rules for SkullRender.
metadata:
  version: 1.0.0
  author: SkullRender AI
  tags: [typescript, quality, strict]
---

# SKILL: TypeScript Strict

> [!IMPORTANT]
> **Regla de Oro**: Si compila, debe ser correcto. Confía en el sistema de tipos.

## Critical Patterns

### 1. Tipado Estricto
*   **No Any**: `any` está prohibido. Usar `unknown` si el tipo es desconocido al principio.
*   **Return Types**: Todas las funciones deben declarar explícitamente qué retornan.
*   **Strict Null Checks**: Asumir que los valores pueden ser `null` o `undefined` y manejarlos.

### 2. Estructuras de Datos
*   **No Enums**: Preferir `const` assertions o Union Types.
    *   *Bad*: `enum Role { Admin, User }`
    *   *Good*: `type Role = 'Admin' | 'User';` o `const Roles = { Admin: 'Admin' } as const;`
*   **Immutability**: Usar `readonly` en arrays y propiedades siempre que sea posible.

### 3. Utility Types
*   Usar `Pick`, `Omit`, `Partial` para derivar tipos en lugar de duplicar interfaces.
*   Usar Zod para validar datos en tiempo de ejecución (que coincidan con los tipos estáticos).

## Anti-Patterns

*   ❌ Usar `!` (Non-null assertion) a menos que sea 100% seguro (ej: tests).
*   ❌ Interfaces con prefijo `I` (`IUser`).
*   ❌ Tipos "Spaghetti" anidados inline (extraer a `types.ts`).

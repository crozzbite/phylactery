---
name: clean-code
description: Standard for Sanitization and Strict Typing (SkullRender Proof)
---

# Clean Code & Type Safety Standard

This skill ensures that all code produced or modified by Antigravity for SkullRender projects adheres to professional engineering standards regarding type safety and clean imports.

## 1. Zero `Any` Policy
- **Prohibition**: The use of `Any` (TypeScript or Python) is strictly forbidden for known structures.
- **Action**: Always define precise interfaces, types, or Pydantic models.
- **Hierarchy Role**: Level 0 (Base Logic). Must be enforced before considering structural bones or technical implementation.
- **Fallback**: If the structure is truly unknown or external, use `Dict[str, object]` (Python) or `Record<string, unknown>` (TypeScript) instead of `Any`.

## 2. Import Hygiene (Zero Residue)
- **Prohibition**: No unused imports should exist in the final codebase.
- **Refactoring Residue**: Be extremely vigilant when changing parameter types (e.g., from `Request` to `Dict`). Always remove the corresponding import immediately.
- **Action**: Every time a file is edited, scan for unused declarations and remove them.
- **Optimization**: Favor specific imports over wildcard imports.

## 3. Trigger & Enforcement
- This skill MUST be applied automatically during the **EXECUTION** and **VERIFICATION** phases of every task.
- Before considering a file change complete, perform a "Sanitization Pass" to verify:
    1. Are there any `Any` types that can be specified?
    2. Are there any `import` statements not utilized in the code?

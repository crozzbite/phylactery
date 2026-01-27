---
name: angular
description: Official SkullRender Angular Standards (v17+).
metadata:
  version: 1.0.0
  author: SkullRender AI
  tags: [angular, frontend, signals, standalone]
---

# SKILL: Angular Moderno (SkullRender Standard)

> [!IMPORTANT]
> **Filosofía**: Componentes Standalone, Signals para estado y Rendimiento.
> Basado en la documentación oficial de Angular y el estándar Gentleman.
>
> **Documentation**: [angular.dev](https://angular.dev/)

## Related Workflows

- [`/create-angular19-app-global`](../../../.agent/workflows/create-angular19-app-global.md) — Create new Angular 19 app with SSR and GitHub integration

## When to Use
*   Siempre que se escriba código Angular (Componentes, Servicios, Pipes).
*   En refactorizaciones de módulos legacy a Standalone.

## Critical Patterns (The "Must Haves")

### 1. Arquitectura de Componentes
*   **Standalone**: Todo componente debe ser `standalone: true`.
*   **ChangeDetection**: Siempre `ChangeDetectionStrategy.OnPush`.
*   **Inject**: Usar `inject()` en lugar de inyección por constructor.

### 2. Gestión de Estado (Signals)
*   **Inputs**: Usar `input()` y `input.required()`.
*   **Outputs**: Usar `output()`.
*   **State**: Preferir `signal()` y `computed()` sobre `BehaviorSubject` para estado síncrono local.
*   **Effects**: Usar `effect()` con precaución, solo para efectos secundarios (logging, sync manual).

### 3. Control Flow & Defer
*   **Sintaxis**: Usar `@if`, `@for`, `@switch` (Nuevo Control Flow).
*   **Defer**: Usar `@defer` para cargar componentes pesados no visibles en el viewport inicial.

## Anti-Patterns (The "Never Do's")

*   ❌ Usar `NgModules` (salvo excepciones muy justificadas).
*   ❌ Suscribirse manualmente en componentes (`.subscribe()`) sin manejar la desuscripción (preferir `async` pipe o Signals).
*   ❌ Usar decoradores viejos `@Input()`, `@Output()` (preferir Signals API).
*   ❌ Lógica de negocio compleja dentro del componente (mover a Servicios/Facades).

## Code Examples

### Good: Modern Component
```typescript
@Component({
  standalone: true,
  selector: 'app-user-profile',
  imports: [CommonModule, UserAvatarComponent],
  template: `
    @if (user(); as u) {
      <app-user-avatar [url]="u.avatarUrl" />
      <h1>{{ u.name }}</h1>
    } @else {
      <p>Loading...</p>
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UserProfileComponent {
  private userService = inject(UserService);
  
  // Signal Input
  userId = input.required<string>();
  
  // Computed State
  user = toSignal(this.userService.getUser(this.userId()));
}
```

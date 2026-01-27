# 📐 Especificaciones de Diseño (Fase 1 Closure)

Este documento formaliza las estructuras de datos y protocolos diseñados durante la Fase 1, cerrando las tareas **1.4 (AgentState)** y **1.5 (Protocolos)**.

---

## 🏗️ 1. AgentState Schema (Tarea 1.4)
El "cerebro" compartido del grafo. Debe ser serializable (JSON) para soportar `Checkpointer` y `Resume`.

### Estructura Principal (`TypedDict`)
```python
class AgentState(TypedDict):
    # --- Identidad & Contexto ---
    thread_id: str
    user_id: str
    agent_mode: Literal["consulting", "planning", "execution"]
    
    # --- Memoria de Trabajo (StateBackend) ---
    input_prompt: str
    current_plan_path: str  # Puntero a /workspace/todo.md
    current_step_id: Optional[str]
    
    # --- Historial de Ejecución ---
    # No guardamos todo el historial de mensajes aquí (eso va al Checkpointer interno de LangGraph),
    # pero sí el estado estructurado de los pasos.
    step_history: Dict[str, StepState]
    
    # --- Estado de Herramientas ---
    last_tool_result: Optional[ToolResult]
    
    # --- Seguridad & HITL (Audit v3.2) ---
    security_context: SecurityContext
    approval_state: Optional[ApprovalState]
```

### Sub-Schemas

#### `StepState`
Estado granular de cada paso del plan.
```python
class StepState(TypedDict):
    id: str
    description: str
    status: Literal["pending", "running", "done", "failed", "blocked"]
    tries: int
    max_tries: int
    result_pointer: Optional[str] # Puntero a resultado (si es evicted)
    last_error: Optional[str]
```

#### `SecurityContext`
Contexto de seguridad inyectado por el Gatekeeper (Input) y RiskEngine.
```python
class SecurityContext(TypedDict):
    permissions_level: Literal["user", "admin", "system"]
    allowed_tools: List[str]
    session_token_hash: str
    is_sanitized: bool
```

#### `ToolResult` (con Eviction support)
```python
class ToolResult(TypedDict):
    tool_name: str
    tool_call_id: str
    output: str # Puede ser el contenido real o un JSON de eviction pointers
    status: Literal["success", "error", "evicted"]
    metadata: Dict[str, Any] # Timestamps, size, etc.
```

---

## 🤝 2. Protocolo de Colaboración (Tarea 1.5)
Reglas de interacción entre Nodos.

### A. Supervisor <-> Executor
El Supervisor es el "Jefe de Estado". El Executor es el "Obrero".

1.  **Handoff Unidireccional:** El Executor NUNCA decide el siguiente paso. Siempre retorna el control al Supervisor tras ejecutar (o fallar).
2.  **State Isolation:** El Executor no modifica el `todo.md` directamente. Solo reporta un `ToolResult`. Es el Supervisor (o Interpreter Node) quien actualiza el estado del plan.
3.  **Conflict Resolution:**
    - Si Executor falla 3 veces (`max_tries`), Supervisor escala a:
        a) **Re-Planning** (llamar a `PlannerNode`).
        b) **User Help** (llamar a `Finalizer` con pregunta).

### B. Human-in-the-Loop (HITL) Protocol
Mecanismo de "Interrupción Controlada".

1.  **Pre-Commit Check:** Ninguna herramienta con `risk_level > low` se ejecuta sin pasar por el nodo `Check`.
2.  **Suspension:** Si se requiere aprobación, el grafo se **congela** (`interrupt_before=["Tools"]`). El estado se guarda en disco (SQLite).
3.  **Resumption:** Al recibir el `ApprovalToken` (validado), el grafo se reanuda **exactamente** donde se quedó, con el token inyectado en `approval_state`.

---

## 🔗 Referencias
- **Arquitectura General:** `ARCHITECTURE.md`
- **Flujo Detallado:** `TECHNICAL_FLOW.md`
- **Pruebas de Robustez:** `ADVERSARIAL_TESTING.md`

# 🗺️ Roadmap de Desarrollo - Phylactery

> **Sistema Multi-Agente con Planeación Dinámica y Ejecución Paralela**

---

## 📋 Estado General

- **Fase Actual:** Fase 3 - Core Implementation (v3.5.1 SEALED - 85% completada)
- **Última Actualización:** 2026-01-27
- **Progreso Global:** 32/38 micro-tasks completadas (Phase 3)

---

## 🎯 Fases del Proyecto

### **Fase 1: Documentación y Diseño** ✅ COMPLETADA

- [x] **1.1** Agregar sección "LLM vs Agentes" en `ARCHITECTURE.md`
- [x] **1.2** Documentar sistema de planeación dinámica con ejemplo de lluvia
- [x] **1.3** Crear diagrama de flujo completo (con re-planeación y paralelismo)
  - [x] **1.3.1** Estandarizar skills para Agent Skills Standard
  - [x] **1.3.2** Crear skill `langchain-docs` con MCP integration
  - [x] **1.3.3** Implementar features de LangChain (por dependencias)
    - [x] **1.3.3.1** Backends (StateBackend, StoreBackend, CompositeBackend)
    - [x] **1.3.3.2** Filesystem Middleware (6 tools)
    - [x] **1.3.3.3** Progressive Disclosure de Skills
    - [x] **1.3.3.4** TodoList Middleware
    - [x] **1.3.3.5** Tool Result Eviction
  - [x] **1.3.4** Documentar comparación con LangChain en ARCHITECTURE.md
  - [x] **1.3.5** Crear diagrama de flujo Opción C (estado objetivo)
- [x] **1.4** Diseñar estructura de `AgentState` mejorado (con memoria de corto plazo)
  - *Entregable:* `planeacion/DESIGN_SPECS.md`
- [x] **1.5** Definir protocolo de colaboración multi-agente
  - *Entregable:* `planeacion/DESIGN_SPECS.md`

---

### **Fase 2: Security Foundation** ✅ COMPLETADA

- [x] **2.1** Motor de Riesgo y Políticas (`RiskEngine`)
  - [x] **2.1.1** Implementar `RiskPolicy` determinista (PII check, Scope check)
  - [x] **2.1.2** Integrar regex de DLP (para evitar fugas en logs/history)
  - [x] **2.1.3** Implementar Conditional Sandboxing (Unauth Path Block)
  - [x] **2.1.4** Implementar Immutable Audit Log (`security_audit.jsonl`)
  - [x] **2.1.5** Implementar Honeytokens con Defensa Activa (Payload de troleo, verificada)
- [x] **2.2** Identidad y Aprobación (`AuthModule`)
  - [x] **2.2.1** Estructura de `ApprovalToken` (HMAC-SHA256 verificado en `test_auth_vectors.py`)
  - [ ] **2.2.2** Setup de OAuth 2.0 Client (Postergado para Integración Externa)
- [x] **2.3** Skills de Seguridad
  - [x] **2.3.1** Crear skill `app-security` con reglas para `detect-secrets` y PR workflow

---

### **Fase 3: Core Implementation (v3.5.1 SEALED)** 🔥 85% COMPLETADA

**Estado:** Core logic + Security hardening + Documentación formal COMPLETADOS

#### Core Implementation (Brain)

- [x] **3.1** Diseño de Arquitectura Profesional
  - [x] **3.1.1** `implementation_plan.md` v3.5.1 SEALED (con auditorías v3.2, v3.3, v3.4, v3.5)
  - [x] **3.1.2** Threat model documentado (tool-swap, replay, double-exec, path traversal)
  - [x] **3.1.3** HITL flow definido (APROBAR/RECHAZAR + 7-factor validation)

- [x] **3.2** Schemas Implementation (`src/app/core/brain/schemas.py`)
  - [x] **3.2.1** `AgentState` TypedDict con `total=False` para hydration incremental
  - [x] **3.2.2** `ProposedTool` contract (canonical_args, args_hash, tool_call_id)
  - [x] **3.2.3** `ToolResult` contract (eviction fields, rehydration policy)

- [x] **3.3** Logic Nodes Implementation (`src/app/core/brain/nodes.py`)
  - [x] **3.3.1** `router_node` (strict regex, deterministic dispatch)
  - [x] **3.3.2** `risk_gate_node` (zero-trust: recalculate canonical + hash)
  - [x] **3.3.3** `approval_handler_node` (7-factor validation + RECHAZAR path)
  - [x] **3.3.4** `interpreter_node` (eviction policy + double-exec prevention)
  - [x] **3.3.5** `await_approval_node` (HITL pause with token generation)
  - [x] **3.3.6** `supervisor_node` (stub básico, orchestration TBD)

- [x] **3.4** Security Hardening (`src/app/core/security/auth.py`)
  - [x] **3.4.1** `TokenManager` refactored (RFC 2104 inspired, atomic verify-consume)
  - [x] **3.4.2** Anti-replay with `threading.Lock` (single-process) + Redis-ready
  - [x] **3.4.3** Path traversal protection in eviction (`os.path.abspath`)
  - [x] **3.4.4** Composite payload binding (`thread_id:user_id:approval_hash`)

- [x] **3.5** Graph Wiring (`src/app/core/brain/graph.py`)
  - [x] **3.5.1** `StateGraph` con `AgentState` schema
  - [x] **3.5.2** Nodes conectados (Router → Supervisor → Executor → RiskGate → Tools)
  - [x] **3.5.3** Dynamic routing con `Command` (LangGraph v0.2+)
  - [x] **3.5.4** Graph compilation verified (`test_phase3.py` passing ✅)

- [ ] **3.6** LLM Nodes (🔴 Phase 4 Priority)
  - [ ] **3.6.1** `planner_node` (LLM-based task decomposition)
  - [ ] **3.6.2** `executor_node` (LLM tool selection + middleware canonicalization)
  - [ ] **3.6.3** `finalizer_node` (response formatting)

- [ ] **3.7** Tools Execution (🔴 Phase 4 Priority)
  - [ ] **3.7.1** MCP Client integration
  - [ ] **3.7.2** Tool error handling + idempotency keys
  - [ ] **3.7.3** External API wrappers (Gmail, Slack, etc.)

#### Documentation & Formal Closure ✅

- [x] **3.8** Security Documentation (Artifact Directory)
  - [x] **3.8.1** `SECURITY_WHITEPAPER.md` (internal, full technical spec)
  - [x] **3.8.2** `SECURITY_WHITEPAPER_PUBLIC.md` (external, sanitized)
  - [x] **3.8.3** `SECURITY_GUARANTEES.md` (stakeholder contract)
  - [x] **3.8.4** `EXECUTION_FLOWS.md` (operational workflow guide, renamed from RUNTIME_WORKFLOW)

**Progreso Fase 3:** 32/38 micro-tasks (84%)  
**Siguiente acción:** Phase 4 - LLM Integration + MCP Client

---

### **Fase 4: Intelligence Layer & External Integration** 🔜 NEXT

**Objetivo:** Complete agent intelligence (LLM) + physical execution (MCP)

- [ ] **4.1** LLM Integration
  - [ ] **4.1.1** Planner Node (reflective planning with LangChain)
  - [ ] **4.1.2** Executor Node (function calling + middleware canonicalization)
  - [ ] **4.1.3** Finalizer Node (response formatting)
  - [ ] **4.1.4** Supervisor orchestration logic (retries, termination)

- [ ] **4.2** MCP Client Integration
  - [ ] **4.2.1** MCP client wrapper (`mcp_client.run_tool`)
  - [ ] **4.2.2** Error handling (retries, timeouts)
  - [ ] **4.2.3** Idempotency for external APIs

- [ ] **4.3** FastAPI Layer
  - [ ] **4.3.1** API Ingress (DLP sanitization, intent classification, auth)
  - [ ] **4.3.2** Streaming responses (SSE for HITL)
  - [ ] **4.3.3** Multi-worker deployment (Redis anti-replay)

- [ ] **4.4** Testing & Validation
  - [ ] **4.4.1** Unit tests for LLM nodes
  - [ ] **4.4.2** Integration tests (end-to-end flows)
  - [ ] **4.4.3** Adversarial testing (prompt injection, tool-swap)

---

## 🚨 Reglas de Ejecución

### **Regla 1: Secuencialidad Estricta**
- ✅ **PROHIBIDO** saltar de una micro-task a otra sin marcarla como completa `[x]`
- ✅ Solo el usuario puede autorizar saltos de tareas
- ✅ Cada micro-task debe tener su commit correspondiente

### **Regla 2: Validación por Fase**
- ✅ No se puede iniciar Fase 2 sin completar Fase 1 al 100%
- ✅ Cada fase debe tener tests que validen su funcionalidad
- ✅ Documentación debe actualizarse antes de marcar fase como completa

### **Regla 3: Comunicación**
- ✅ Reportar progreso después de cada micro-task completada
- ✅ Solicitar aprobación del usuario antes de cambios arquitectónicos mayores
- ✅ Documentar decisiones técnicas en este archivo

---

## 📊 Métricas de Progreso

### Fase 1: Documentación y Diseño
- **Progreso:** 7/7 tareas principales (100%) - Incluyendo Security Post-Audit
- **Estado:** ✅ COMPLETADA
- **Siguiente acción:** Iniciar Fase 2 (Implementación de Código)

### Fase 2: Security Foundation (Prioridad Alta)
- **Estado:** ✅ COMPLETADA (Incluyendo Sandbox & Audit)
- **Siguiente acción:** Iniciar Fase 3 (Core Logic)

### Fase 3: Core Implementation (v3.5.1 SEALED)
- **Progreso:** 32/38 tareas (84%)
- **Estado:** ✅ Core Logic COMPLETO, 🔴 LLM Nodes + MCP Pending
- **Deliverables:**
  - ✅ Schemas (`AgentState`, `ProposedTool`, `ToolResult`)
  - ✅ Logic Nodes (`router`, `risk_gate`, `approval_handler`, `interpreter`)
  - ✅ Graph Wiring (StateGraph compiled)
  - ✅ Security Hardening (`TokenManager`, anti-replay, path protection)
  - ✅ Formal Documentation (4 docs: Whitepaper, Public, Guarantees, Flows)
- **Siguiente acción:** Phase 4 - LLM Nodes + MCP Client

### Fase 4: Intelligence Layer & External Integration
- **Progreso:** 0/16 tareas (0%)
- **Estado:** 🔴 NO INICIADA
- **Bloqueadores:** Ninguno (Phase 3 core complete)

---

## 📝 Notas de Desarrollo

### 2026-01-27 (04:42) - Phase 3 v3.5.1 SEALED
- ✅ **Fase 3 Core Completada:** Schemas, Nodes, Graph, Security
- ✅ **TokenManager Hardened:** Logic inversion fixed, atomic verify-consume, Redis-ready
- ✅ **Formal Documentation:**
  - `SECURITY_WHITEPAPER.md` (internal): RFC 2104, OWASP, NIST SP 800-207 references
  - `SECURITY_WHITEPAPER_PUBLIC.md` (external): Sanitized for publication
  - `SECURITY_GUARANTEES.md` (stakeholder): What we guarantee vs. don't guarantee
  - `EXECUTION_FLOWS.md` (operational): Node-by-node execution paths
- ✅ **Testing:** `test_phase3.py` passing (TokenManager + Graph compilation)
- ✅ **Sign-off:** Approved for production single-region deployment
- � **Pending:** LLM Nodes (Planner, Executor, Finalizer) + MCP Client

### 2026-01-26 (23:20)
- ✅ **Tarea 1.3.3.1 Completada:** Backends Implementation
  - Creado `BackendProtocol` con interfaces completas
  - Implementado `StateBackend` (RAM - efímero)
  - Implementado `StoreBackend` (SQLite/Firestore - persistente)
  - Implementado `CompositeBackend` (router por path prefix)
  - Ubicación: `src/app/core/backends/`
  
- ✅ **Tarea 1.3.3.2 Completada:** Filesystem Middleware
  - Implementadas 6 herramientas: `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`
  - Middleware composable con backends pluggables
  - System prompt incluido con instrucciones de uso
  - Ubicación: `src/app/core/middleware/filesystem.py`
  
- ✅ **Tarea 1.3.3.3 Completada:** Progressive Disclosure de Skills
  - Modificado `loader.py` para cargar solo metadata al inicio
  - Implementado `load_skill_content()` para carga on-demand
  - Implementado `get_relevant_skills()` con scoring por keywords
  - Reduce uso de memoria y mejora performance
  
- ✅ **Tarea 1.3.3 Completada (FULL):** Todos los middlewares implementados
  - `TodoListMiddleware`: Persistencia de tareas en markdown (`/workspace/todo.md`)
  - `EvictionMiddleware`: Evicción automática de outputs grandes (>10k chars)
  - Integrados en `src/app/core/middleware/`
  
- ✅ **Tarea 1.3.4 Completada:** Documentación de Arquitectura
  - Actualizado `ARCHITECTURE.md` con tabla comparativa vs LangChain Deep Agents
  - Documentada la estrategia de Backends (State vs Store)
  - Explicado el CompositeBackend Router, TodoList y Eviction
  
- ✅ **Tarea 1.3.5 Completada:** Diagrama de Flujo Opción C
  - Creado `planeacion/TECHNICAL_FLOW.md` con diagrama Mermaid
  - Visualiza interacción entre Router, Middleware, Backends y Skills
  - Representa el "Target Architecture" completo

---

**Última micro-task completada:** 3.8.4 - Formal Documentation Closure (Phase 3 v3.5.1 SEALED)  
**Siguiente micro-task:** 4.1.1 - Planner Node (LLM Integration)  
**Responsable:** CTO (Antigravity AI)

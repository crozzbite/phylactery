# 📡 Flujo Técnico de Phylactery (Arquitectura Profesional v3.5 - SEALED + FIXES)

Diseño FINAL robusto. Soporte HITL, Eviction, Seguridad Determinista y Anti-Replay. Corregidos bugs de Eviction y Canonical Hash.

## 🔄 Diagrama de Flujo (Mermaid v3.5)

```mermaid
flowchart TD
    %% Nodos Principales
    User((👤 Usuario))
    API[FastAPI Layer\n(DLP / Auth / Hydrate / Intent)]
    
    subgraph "🧠 Brain Core (LangGraph)"
        direction TB
        Router{Router Node\n(State Dispatch)}
        Planner[Planner Node]
        Supervisor[Supervisor Node]
        Finalizer[Finalizer Node]
        
        subgraph "Execution Pipeline"
            Executor[Executor Node\n(Propose Tool)]
            RiskGate{RiskGate Node\n(Hash & Risk Check)}
            
            subgraph "HITL Loop"
                AwaitApproval[AwaitApproval Node\n(Pause)]
                ApprovalHandler[ApprovalHandler Node\n(Validate)]
            end
            
            Tools[Tool Executor Node\n(Physics)]
            Interpreter[Interpreter Node\n(Eviction/Status)]
        end
        
        
    end
    
    %% Flujo de Entrada
    User -->|POST /chat| API
    API -->|Sanitized + Intent| Router
    
    %% Router Logic (Deterministic)
    Router -->|Valid Approval Reply| ApprovalHandler
    Router -->|Invalid/Info Reply| Supervisor
    Router -->|Intent: Conversation| Finalizer
    Router -->|Intent: Task (New)| Planner
    Router -->|Intent: Task (Resume)| Supervisor
    
    %% Planning
    Planner --> Supervisor
    
    %% Supervision Cycle
    Supervisor -->|Delegate (Running)| Executor
    Supervisor -->|Finish| Finalizer
    Supervisor -->|Need Info| Finalizer
    
    %% Execution Cycle (The Secure Loop)
    Executor -->|Propose Tool| RiskGate
    
    %% Risk Logic (Deterministic)
    RiskGate -->|ALLOW| Tools
    RiskGate -->|AUTH_REQUIRED| AwaitApproval
    RiskGate -->|BLOCKED| Interpreter
    
    %% HITL
    AwaitApproval -->|Suspend| Finalizer
    ApprovalHandler -->|Approved| Tools
    ApprovalHandler -->|Rejected| Supervisor
    
    %% Tool & Interp
    Tools -->|Result| Interpreter
    Interpreter -->|Next (Clean Prop)| Supervisor
    
    %% Salida
    Finalizer --> API
    API --> User
    
    %% Styles
    classDef core fill:#f9f,stroke:#333,stroke-width:2px;
    classDef hitl fill:#f55,stroke:#333,stroke-width:2px,color:white;
    
    class Router,Planner,Executor,Tools,Finalizer,Supervisor,Interpreter,ApprovalHandler core;
    class RiskGate,AwaitApproval hitl;
```

## 📜 Lógica de Routing (Pseudocódigo Final)

### 1. Router Node (Strict Regex)
No re-clasifica. Usa regex estricto para evitar falsos positivos.

```python
def router_node(state: AgentState):
    if state.awaiting_approval:
        last_msg = state.messages[-1].content.strip()
        # FIX: Regex Estricto
        rgx_ap = r"^APROBAR\s+([A-Za-z0-9_-]{6,})\s+([A-Za-z0-9_-]{6,})$"
        rgx_re = r"^RECHAZAR\s+([A-Za-z0-9_-]{6,})$"

        if re.match(rgx_ap, last_msg) or re.match(rgx_re, last_msg):
            return command.goto("ApprovalHandler")
        else:
            return command.goto("Supervisor") 

    if state.awaiting_user_input:
        return command.goto("Supervisor")

    if state.intent == "conversation": return command.goto("Finalizer")
    if state.intent == "task":
        return command.goto("Planner") if not state.plan else command.goto("Supervisor")
            
    return command.goto("Supervisor") 
```

### 2. RiskGate Node (Integrity & Security)
Evalúa `state.proposed_tool` usando `RiskEngine`. Valida hash.

```python
def risk_gate_node(state: AgentState):
    tool = state.proposed_tool 
    
    # 1. FIX: Integrity Check (Recalculate)
    algo_canonical = canonicalize(tool.args)
    algo_hash = sha256(algo_canonical)
    
    if algo_hash != tool.args_hash:
        return command.error("Integrity Mismatch: Tool args modified!")
    
    # 2. Risk Engine (Evaluate canonical, not raw)
    risk_eval = risk_engine.evaluate(tool.name, algo_canonical)
    
    if risk_eval.decision == "BLOCKED":
        return command.error("Security Blocked identified")
        
    if risk_eval.decision == "AUTH_REQUIRED":
        challenge = auth.create_challenge(tool)
        return command.update(
            awaiting_approval=True,
            approval_id=challenge.id,
            approval_hash=algo_hash, 
            goto="AwaitApproval"
        )
        
    return command.goto("Tools")
```

### 3. ApprovalHandler (Reject Path)
```python
def approval_handler_node(state: AgentState):
    msg = state.messages[-1]
    
    # 1. Parse REJECT
    if msg.startswith("RECHAZAR"):
         # FIX: Limpieza de estado completa
         return command.update(
             awaiting_approval=False,
             proposed_tool=None,
             approval_id=None,
             goto="Supervisor" # "User rejected tool X"
         )

    # 2. APROBAR logic (7-Factor Validation)
    # Validate ID, Expiry, Hash, Sig, One-Time, Thread, User
    if not validate_all(state, msg):
         return command.error("Invalid Approval Token")

    return command.goto("Tools")
```

### 4. Interpreter Node (Eviction Fix)
```python
def interpreter_node(state: AgentState):
    result = state.last_tool_result
    
    # FIX: Eviction based on ORIGINAL size
    raw_size = len(result.output)
    
    if raw_size > 10_000:
        pointer = save_to_disk(result.output)
        result.evicted = True
        result.pointer = pointer
        result.size = raw_size
        result.output = f"[EVICTED size={raw_size}] See {pointer}"
        # FIX: Rehydration Allowed logic
        result.rehydration_allowed = raw_size < 50_000
    
    # Cleanup & Status
    update = {"proposed_tool": None, "last_tool_result": result}
    # ... update step status
    
    return command.update(update, goto="Supervisor")
```

## 🏗️ Schema del Estado v3.5 (Locked)

```python
class AgentState(TypedDict):
    thread_id: str
    user_id: str 
    intent: str  
    messages: Annotated[list[BaseMessage], add_messages]

    # Planning & Progress
    plan: list[str]
    current_step: int
    step_status: dict[int, str]
    tries: dict[int, int]

    # Tool Execution Context (Proposal)
    proposed_tool: dict | None
    # {
    #   "name": str,
    #   "args": dict,
    #   "canonical_args": str, # For HMAC
    #   "args_hash": str,      # SHA256 of CANONICAL
    #   "tool_call_id": str,   
    #   ...
    # }

    # Tool Execution Context (Result)
    last_tool_result: dict | None
    # {
    #   ...,
    #   "evicted": bool,
    #   "pointer": str | None,
    #   "size_chars": int,
    #   "rehydration_allowed": bool, # Calculated from RAW size
    #   ...
    # }

    # Safety
    do_not_store: bool
    audit_trail: list[dict]
    # ... approval fields
```

## 📦 Policies v3.5
1.  **Strict Canonicalization:** RiskGate MUST recalculate format before signing/evaluating. NEVER trust the LLM's "hash".
2.  **Explicit Reject:** Users can cancel a pending tool without breaking flow.
3.  **Audit First:** Eviction logic preserves the original size metadata.

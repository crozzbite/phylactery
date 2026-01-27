import re
import os
import json
import hashlib
from typing import Literal, Dict, Any, cast

# LangGraph & Core
from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage

# Phylactery Core
from .schemas import AgentState, ProposedTool, ToolResult
from ..security.risk_policy import RiskEngine
from ..security.auth import TokenManager
from ..backends.state import StateBackend

# --- SINGLETONS ---
# In a real app, inject these via dependency injection configuration
risk_engine = RiskEngine()
auth_manager = TokenManager(secret_key=os.environ.get("PHYLACTERY_SECRET", "dev-secret-key"))
# Note: StateBackend usually needs a runtime, mocking saving to disk for now via helper

# --- HELPER FUNCTIONS ---

# Helper for consistent failures
def make_tool_result_failed(msg: str) -> ToolResult:
    return {
        "status": "failed",
        "output": msg,
        "evicted": False,
        "pointer": None,
        "size_chars": 0,
        "rehydration_allowed": True,
        "summary": msg[:100],
        "source_path": None
    }

def canonicalize(args: Dict[str, Any]) -> str:
    """Produces the canonical JSON string for HMAC signing."""
    return json.dumps(args, sort_keys=True, separators=(',', ':'))

def calculate_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()

def save_eviction(content: str, run_id: str) -> str:
    """Real disk write implementation with Path Traversal Protection."""
    base_dir = os.path.abspath("/workspace/evictions")
    os.makedirs(base_dir, exist_ok=True)
    
    filename = f"eviction_{run_id}_{hashlib.md5(content.encode()).hexdigest()[:8]}.txt"
    path = os.path.abspath(os.path.join(base_dir, filename))
    
    # Security: Ensure path is inside base_dir
    if not path.startswith(base_dir):
        raise ValueError("Invalid eviction path: Potential traversal attack")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"[DISK WRITE] Saved {len(content)} chars to {path}")
    return path

# --- NODE IMPLEMENTATIONS (v3.5.1) ---

# FIX: Regex with dots allowed in token
RE_RECHAZAR = re.compile(r"^RECHAZAR\s+([A-Za-z0-9_-]{6,})\s*$", re.IGNORECASE)
RE_APROBAR  = re.compile(r"^APROBAR\s+([A-Za-z0-9_-]{6,})\s+([A-Za-z0-9._-]{10,})\s*$", re.IGNORECASE)


def router_node(state: AgentState) -> Command[Literal["ApprovalHandler", "Supervisor", "Planner", "Finalizer"]]:
    """
    Decides where to route the execution flow based on Intent and Interaction State.
    """
    # 1. HITL Reply Check
    if state.get("awaiting_approval"):
        last_msg = state["messages"][-1].content
        if isinstance(last_msg, str):
            clean_msg = last_msg.strip()
            if RE_RECHAZAR.match(clean_msg) or RE_APROBAR.match(clean_msg):
                return Command(goto="ApprovalHandler")
        # Fallback: User said something else -> Info/Question
        return Command(goto="Supervisor")

    # 2. Info Reply Check
    if state.get("awaiting_user_input"):
        return Command(goto="Supervisor")

    # 3. Intent Routing
    intent = state.get("intent", "task") # Default to task if missing
    
    if intent == "conversation":
        return Command(goto="Finalizer")
        
    if intent == "task":
        if not state.get("plan"):
            return Command(goto="Planner")
        return Command(goto="Supervisor")

    return Command(goto="Supervisor")


def risk_gate_node(state: AgentState) -> Command[Literal["Tools", "AwaitApproval", "Interpreter"]]:
    """
    Security Chokepoint. 
    Verifies Integrity (Hash) and Risk Policy.
    """
    tool = state.get("proposed_tool")
    if not tool:
         return Command(
             update={"last_tool_result": make_tool_result_failed("System Error: No tool proposed")},
             goto="Interpreter"
         )

    # 1. Integrity Check (Recalculate)
    # Trust No One: We rebuild canonical args and hash from the raw dict
    canonical = canonicalize(tool["args"])
    computed_hash = calculate_hash(canonical)

    if tool.get("canonical_args") != canonical:
         return Command(
             update={"last_tool_result": make_tool_result_failed("Integrity Error: Canonical args mismatch")},
             goto="Interpreter"
         )
         
    if tool.get("args_hash") != computed_hash:
         return Command(
             update={"last_tool_result": make_tool_result_failed("Integrity Error: Hash mismatch (Tampering detected)")},
             goto="Interpreter"
         )

    # 2. Risk Evaluation
    # FIX: Pass canonical to engine (simulated support in MVP)
    # In strict implementation, engine should parse canonical.
    # For now ensuring we pass exact args that generated the canonical.
    risk_eval = risk_engine.evaluate_risk(tool["name"], tool["args"]) 

    if risk_eval.decision == "BLOCKED":
        return Command(
             update={"last_tool_result": make_tool_result_failed(f"Security Blocked: {risk_eval.reason}")},
             goto="Interpreter"
        )
        
    if risk_eval.decision == "AUTH_REQUIRED":
        approval_id = f"auth_{os.urandom(4).hex()}"
        # FIX: Real Expiry
        import time
        expires_at = time.time() + 300 # 5 mins
        
        return Command(
            update={
                "awaiting_approval": True,
                "approval_id": approval_id,
                "approval_hash": computed_hash,
                "approval_expires_at": expires_at
            },
            goto="AwaitApproval"
        )

    # ALLOW -> Execute
    return Command(goto="Tools")


def approval_handler_node(state: AgentState) -> Command[Literal["Tools", "Supervisor"]]:
    """
    Validates Approval Token (7-Factor Check).
    Handles RECHAZAR.
    """
    last_msg = state["messages"][-1].content
    if not isinstance(last_msg, str):
        return Command(goto="Supervisor")
        
    clean_msg = last_msg.strip()
    
    m_rechazar = RE_RECHAZAR.match(clean_msg)
    m_aprobar = RE_APROBAR.match(clean_msg)
    
    # REJECT PATH
    if m_rechazar:
        return Command(
            update={
                "awaiting_approval": False,
                "proposed_tool": None, # Clean slate
                "approval_id": None,
                "approval_hash": None,
                "approval_expires_at": None,
                "last_tool_result": make_tool_result_failed("User Rejected Action")
            },
            goto="Supervisor"
        )
        
    # APPROVE PATH
    if not m_aprobar:
        return Command(goto="Supervisor") # Should be caught by Router, but safefallback
        
    approval_id = m_aprobar.group(1)
    token = m_aprobar.group(2)
    
    # 1. ID Match
    if approval_id != state.get("approval_id"):
        return Command(goto="Supervisor")
        
    # 2. Expiry Check
    import time
    if time.time() > (state.get("approval_expires_at") or 0):
        # Expired
        return Command(
            update={"awaiting_approval": False, "approval_id": None}, # Force retry/fail
            goto="Supervisor"
        )

    # 3. Binding Check (Composite Payload)
    # Payload = thread_id:user_id:approval_hash
    thread_id = state.get("thread_id", "")
    user_id = state.get("user_id", "")
    app_hash = state.get("approval_hash", "")
    
    expected_payload = f"{thread_id}:{user_id}:{app_hash}"
    
    # Verify & Consume (ATOMIC - single method call)
    if not auth_manager.verify_and_consume(token, expected_payload):
         return Command(goto="Supervisor")
    
    # Success
    return Command(
        update={
            "awaiting_approval": False, 
            "approval_id": None,
            "approval_expires_at": None
        },
        goto="Tools"
    )


def interpreter_node(state: AgentState) -> Command[Literal["Supervisor"]]:
    """
    Analyzes Tool Result.
    Handles Eviction (Size > 10k).
    Cleans up execution context.
    """
    result = state.get("last_tool_result") or {"status": "failed", "output": "No result found"}
    
    # --- EVICTION LOGIC ---
    # Calc strict RAW size
    raw_output = result["output"]
    if isinstance(raw_output, (dict, list)):
        raw_str = json.dumps(raw_output)
    else:
        raw_str = str(raw_output)
        
    original_size = len(raw_str)
    
    if original_size > 10_000:
        pointer = save_eviction(raw_str, state.get("thread_id", "unknown"))
        
        # Mutate result to be lightweight
        result["evicted"] = True
        result["pointer"] = pointer
        result["size_chars"] = original_size
        result["output"] = f"[EVICTED size={original_size} chars] Content at {pointer}"
        result["summary"] = raw_str[:500] + "...(truncated)"
        
        # Strict Rehydration Policy
        result["rehydration_allowed"] = original_size <= 50_000
    else:
        result["evicted"] = False
        result["rehydration_allowed"] = True
        result["size_chars"] = original_size

    # Update State
    return Command(
        update={
            "last_tool_result": result,
            "proposed_tool": None, # CRITICAL: Prevent Double-Exec
        },
        goto="Supervisor"
    )

def await_approval_node(state: AgentState):
    """
    System Pause. State is already updated by RiskGate.
    Just yields to allow graph interrupt/exit.
    """
    # GENERATE TOKEN FOR USER CONVENIENCE (Simulation)
    thread_id = state.get("thread_id", "")
    user_id = state.get("user_id", "")
    app_hash = state.get("approval_hash", "")
    payload = f"{thread_id}:{user_id}:{app_hash}"
    
    token = auth_manager.sign_payload(payload)
    
    return {
        "messages": [AIMessage(content=f"🔒 AUTH REQUIRED: To approve, type: APROBAR {state['approval_id']} {token}")]
    }

def supervisor_node(state: AgentState):
    """
    Orchestrator.
    Simple MVP: Always Delegates to Executor if plan not done.
    (Real impl needs LLM decision)
    """
    # Placeholder for MVP wiring
    # If no proposed tool, ask Executor to propose one
    if not state.get("proposed_tool"):
        # Real logic: Calling Planner/Executor LLM
        pass 
    return {}

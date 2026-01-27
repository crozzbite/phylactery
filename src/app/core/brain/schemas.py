from typing import TypedDict, Annotated, List, Dict, Optional, Any, Union
import operator
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# --- V3.5.1 CONTRACTS ---

class ProposedTool(TypedDict):
    """
    Contract for Tool Proposal (Executor Output).
    Must NOT be executed directly without RiskGate validation.
    """
    name: str
    args: Dict[str, Any]
    canonical_args: str  # For HMAC binding (normalized JSON string)
    args_hash: str       # SHA256(canonical_args)
    tool_call_id: str    # LangChain compatibility
    step_idx: int
    created_at: float

class ToolResult(TypedDict):
    """
    Contract for Tool Result (Interpreter Input).
    Handles Eviction and Rehydration policy.
    """
    status: str          # "success" | "failed"
    output: Union[str, Dict[str, Any]]
    
    # Eviction Fields
    evicted: bool
    pointer: Optional[str]
    size_chars: int
    rehydration_allowed: bool # Calculated from original raw_size
    
    summary: Optional[str]    # Head of content
    source_path: Optional[str]

# --- AGENT STATE ---

class AgentState(TypedDict):
    """
    The Brain's Working Memory (v3.5.1 Strict).
    Supports HITL, Deterministic Routing, and Audit.
    """
    # Identity & Scope
    thread_id: str
    user_id: str         # For Approval Binding
    intent: str          # "conversation" | "task" | "requirements"
    
    # Message History (Reducer: Append Only)
    messages: Annotated[List[BaseMessage], add_messages]

    # Planning & Progress
    plan: List[str]
    current_step: int
    step_status: Dict[int, str]  # {0: "done", 1: "running"}
    tries: Dict[int, int]        # {1: 2} (2 retries for step 1)

    # Tool Execution Context
    proposed_tool: Optional[ProposedTool]
    last_tool_result: Optional[ToolResult]

    # Interaction State
    awaiting_user_input: bool
    question: Optional[str]
    
    # Approval State (HITL)
    awaiting_approval: bool
    approval_id: Optional[str]
    approval_hash: Optional[str]
    approval_expires_at: Optional[float]

    # Safety & Audit
    do_not_store: bool
    security_findings: List[Dict[str, Any]] # DLP flags
    audit_trail: List[Dict[str, Any]]       # Immutable log replica

from langgraph.graph import StateGraph, START, END
from .schemas import AgentState
from .nodes import (
    router_node,
    risk_gate_node,
    interpreter_node,
    approval_handler_node,
    await_approval_node,
    supervisor_node
)

# --- LLM NODE STUBS (Placeholders for next phase) ---
# In real impl, these import from llm_nodes.py

def planner_node(state: AgentState):
    """Reflective Planner Node."""
    # TODO: Implement LLM Planning
    return {"plan": ["Do step 1", "Do step 2"]}

def executor_node(state: AgentState):
    """Executor Strategy Node (Proposer)."""
    # TODO: Implement LLM Tool Selection
    # For MVP test, propose a safe tool
    return {
        "proposed_tool": {
            "name": "read_file",
            "args": {"path": "README.md"},
            # In real impl, LLM generates this or we inject integrity fields here?
            # NO, LLM generates name/args. 
            # We must canonicalize for it or have a middleware do it.
            # Assuming middleware or post-processing adds canonical fields for security.
            "canonical_args": '{"path":"README.md"}',
            "args_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", # Dummy
            "tool_call_id": "call_123",
            "step_idx": 1,
            "created_at": 1234567890.0
        }
    }

def tools_node(state: AgentState):
    """Physical Tool Execution Node."""
    # TODO: Integrate MCP Client
    tool = state.get("proposed_tool")
    return {"last_tool_result": {"status": "success", "output": f"Simulated content of {tool['args']['path']}"}}

def finalizer_node(state: AgentState):
    """Response Formatter."""
    return {"messages": [{"role": "assistant", "content": "Task Completed"}]}

# --- GRAPH WIRING ---

workflow = StateGraph(AgentState)

# 1. Add Nodes
workflow.add_node("Router", router_node)
workflow.add_node("Planner", planner_node)
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("Executor", executor_node)
workflow.add_node("RiskGate", risk_gate_node)
workflow.add_node("Tools", tools_node)
workflow.add_node("Interpreter", interpreter_node)
workflow.add_node("AwaitApproval", await_approval_node)
workflow.add_node("ApprovalHandler", approval_handler_node)
workflow.add_node("Finalizer", finalizer_node)

# 2. Define Edges
# Start -> Router
workflow.add_edge(START, "Router")

# Router is Dynamic (returns Command) - No static edges needed for it if using Command
# But we must register it as a starting point logic?
# LangGraph with Command returns handles routing implicitly.

# Planner -> Supervisor
workflow.add_edge("Planner", "Supervisor")

# Supervisor -> Executor | Finalizer (Dynamic?)
# Supervisor in nodes.py currently returns dict. It needs logic.
# For now, let's hardwire Supervisor -> Executor for testing loop.
workflow.add_edge("Supervisor", "Executor") 

# Executor -> RiskGate
workflow.add_edge("Executor", "RiskGate")

# RiskGate -> Tools | AwaitApproval | Interpreter (Dynamic Command)

# Tools -> Interpreter
workflow.add_edge("Tools", "Interpreter")

# Interpreter -> Supervisor (Dynamic Command)

# AwaitApproval -> Finalizer (Suspend) - Wait, it pauses.
# If we want to return to user, we go to Finalizer or END?
# AwaitApproval yields messages. We should go to END to wait for user input.
workflow.add_edge("AwaitApproval", "Finalizer")

# ApprovalHandler -> Tools | Supervisor (Dynamic Command)

# Finalizer -> END
workflow.add_edge("Finalizer", END)

# Compile
graph = workflow.compile()

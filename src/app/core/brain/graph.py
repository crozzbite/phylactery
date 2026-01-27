import os
import asyncio
from functools import partial
from langgraph.graph import StateGraph, START, END

# Phase 3 nodes (Router, RiskGate, etc.)
from .schemas import AgentState
from .nodes import (
    router_node,
    risk_gate_node,
    interpreter_node,
    approval_handler_node,
    await_approval_node
)

# Phase 4 core nodes
from .supervisor import supervisor_node
from .llm_nodes import (
    planner_node_impl,
    executor_node_impl,
    finalizer_node_impl
)

# Phase 4 helpers & execution
from .config import get_llm, canonicalize, calculate_hash, validate_tool_args
from ..tools.mcp_runner import MCPToolRunner
from ..tools.registry import get_tool_registry
from ..tools.idempotency import get_idempotency_store, make_idempotency_key

# --- LAZY INITIALIZATION ---

_llm = None
_mcp_runner = None
_graph = None

def get_graph():
    """Lazy constructor for the compiled graph with all dependencies."""
    global _llm, _mcp_runner, _graph
    
    if _graph is not None:
        return _graph
        
    # 1. Initialize LLM (env-based)
    if _llm is None:
        _llm = get_llm()
    
    # 2. Setup MCP Runner
    if _mcp_runner is None:
        _mcp_runner = MCPToolRunner()
    
    # 3. Populate Tool Registry (if runner initialized)
    registry = get_tool_registry()
    
    # 4. Partially apply dependencies to nodes
    planner = partial(planner_node_impl, llm=_llm)
    executor = partial(
        executor_node_impl, 
        llm=_llm, 
        canonicalize=canonicalize, 
        hash_fn=calculate_hash, 
        validate_fn=validate_tool_args
    )
    finalizer = partial(finalizer_node_impl, llm=_llm)

    # 5. Tools node logic with MCP Integration & Idempotency
    async def tools_node_impl(state: AgentState):
        """Physical Tool Execution Node using MCP."""
        from langgraph.types import Command
        
        tool = state.get("proposed_tool")
        if not tool:
            return {"last_tool_result": {"status": "failed", "output": "No proposed_tool"}}
        
        # --- IDEMPOTENCY CHECK ---
        id_store = get_idempotency_store()
        id_key = make_idempotency_key(
            state.get("thread_id", "default"),
            tool.get("step_idx", 0),
            tool.get("args_hash", "")
        )
        
        cached = id_store.get(id_key)
        if cached:
            print(f"[IDEMPOTENCY] Cache hit for {id_key}")
            return {"last_tool_result": cached}

        # Ensure MCP runner is initialized
        if not _mcp_runner.initialized:
            mcp_config = os.getenv("MCP_CONFIG_PATH", ".mcp/config.json")
            await _mcp_runner.initialize(mcp_config)
            # Populat registry after init
            registry.register_from_mcp(_mcp_runner)
        
        result = await _mcp_runner.call(tool["name"], tool["args"])
        
        # Prepare result
        tool_result = None
        if result["ok"]:
            tool_result = {
                "status": "success", 
                "output": result["output"],
                "evicted": False,
                "size_chars": len(str(result["output"]))
            }
        else:
            tool_result = {
                "status": "failed", 
                "output": result["error"],
                "evicted": False,
                "size_chars": 0
            }
            
        # --- CACE RESULT ---
        if tool_result:
            id_store.set(id_key, tool_result)
            
        return {"last_tool_result": tool_result}

    # --- GRAPH WIRING ---
    workflow = StateGraph(AgentState)
    workflow.add_node("Router", router_node)
    workflow.add_node("Planner", planner)
    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("Executor", executor)
    workflow.add_node("RiskGate", risk_gate_node)
    workflow.add_node("Tools", tools_node_impl)
    workflow.add_node("Interpreter", interpreter_node)
    workflow.add_node("AwaitApproval", await_approval_node)
    workflow.add_node("ApprovalHandler", approval_handler_node)
    workflow.add_node("Finalizer", finalizer)

    workflow.add_edge(START, "Router")
    workflow.add_edge("Planner", "Supervisor")
    workflow.add_edge("Tools", "Interpreter")
    workflow.add_edge("AwaitApproval", "Finalizer")
    workflow.add_edge("Finalizer", END)

    _graph = workflow.compile()
    return _graph

# Proxy class for lazy loading the graph
class LazyGraph:
    def __getattr__(self, name):
        return getattr(get_graph(), name)
    def __call__(self, *args, **kwargs):
        return get_graph()(*args, **kwargs)
    async def ainvoke(self, *args, **kwargs):
        g = get_graph()
        return await g.ainvoke(*args, **kwargs)

# Global graph instance (lazy)
graph = LazyGraph()

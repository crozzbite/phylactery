"""
LLM-based nodes for Phase 4: Planner, Executor, Finalizer.

These nodes add intelligence to the agentic runtime while maintaining
Phase 3's zero-trust security guarantees.

Security Principles:
- Server-side canonicalization (never trust LLM hashes)
- Robust JSON parsing with fallbacks
- Max step limits (DoS prevention)
- Path validation before tool proposal
"""

import json
import re
import time
from typing import Dict, Any, List, Literal, Callable
from langgraph.types import Command
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


def parse_llm_json(text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """
    Robust JSON extraction from LLM response.
    
    Strategy:
    1. Check for markdown code blocks (```json ... ```)
    2. Try direct JSON parse
    3. Try non-greedy regex extraction of all {...} candidates
    4. Fall back to provided default
    """
    # 1. Markdown code block extraction
    code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    for block in code_blocks:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue
            
    # 2. Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    
    # 3. Try regex extraction (non-greedy, multiple candidates)
    # Target the largest JSON block if multiple exist
    candidates = re.findall(r'\{[\s\S]*?\}', text)
    for cand in sorted(candidates, key=len, reverse=True):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    
    # 4. Fallback
    return fallback


async def planner_node_impl(
    state: Dict[str, Any],
    llm,
) -> Command[Literal["Supervisor"]]:
    """
    Planner Node: Decompose user goal into atomic steps.
    
    Input State:
    - messages: List[Message] (uses last HumanMessage as goal)
    
    Output State:
    - plan: List[str] (max 8 steps)
    - current_step: 0
    - step_status: {i: "pending"}
    - tries: {i: 0}
    
    Constraints:
    - Max 8 steps (DoS prevention)
    - Atomic, single-action steps
    - No tool names (human-readable actions)
    
    Example:
        Goal: "Send email with weekly report"
        Plan:
        1. Read weekly_report.md
        2. Format report as email
        3. Send email to boss@company.com
    """
    # Extract goal from last human message
    goal = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, 'type') and msg.type == "human":
            goal = str(msg.content)
            break
    
    if not goal:
        goal = "No goal specified"
    
    # Prompt engineering for structured output
    system_prompt = SystemMessage(content=(
        "You are the PLANNER for an AI agent system.\n"
        "Your job: Break down the user's goal into atomic steps.\n\n"
        "RULES:\n"
        "- Return ONLY valid JSON (no markdown, no explanations)\n"
        "- Max 8 steps\n"
        "- Each step: single action, human-readable\n"
        "- Do NOT use tool names (e.g., say 'List files' not 'glob')\n"
        "- Steps should be sequential and logical\n\n"
        'FORMAT: {"plan": ["step1", "step2", ...]}\n'
    ))
    
    user_prompt = HumanMessage(content=f"Goal: {goal}")
    
    # Invoke LLM
    response = await llm.ainvoke([system_prompt, user_prompt])
    
    # Parse with fallback
    data = parse_llm_json(
        str(response.content),
        fallback={"plan": [goal]}  # If parsing fails, use goal as single step
    )
    
    plan = data.get("plan", [goal])
    
    # Enforce max 8 steps
    if len(plan) > 8:
        plan = plan[:8]
    
    # Ensure at least 1 step
    if not plan:
        plan = [goal]
    
    # Initialize tracking state
    step_status = {i: "pending" for i in range(len(plan))}
    tries = {i: 0 for i in range(len(plan))}
    
    return Command(
        update={
            "plan": plan,
            "current_step": 0,
            "step_status": step_status,
            "tries": tries
        },
        goto="Supervisor"
    )


async def executor_node_impl(
    state: Dict[str, Any],
    llm,
    canonicalize: Callable[[Dict], str],
    hash_fn: Callable[[str], str],
    validate_fn: Callable[[str, Dict], tuple]
) -> Command[Literal["RiskGate", "Finalizer", "Interpreter"]]:
    """
    Executor Node: Propose tool call for current step.
    
    Input State:
    - plan: List[str]
    - current_step: int
    
    Output State:
    - proposed_tool: ProposedTool (with server-side canonical/hash)
    
    Security:
    - Server-side canonicalization (zero-trust)
    - Path validation before proposal
    - Tool whitelist enforcement
    
    Flow:
    - LLM proposes {"name": "...", "args": {...}}
    - We validate args server-side
    - We construct canonical/hash server-side
    - We create ProposedTool
    """
    # Get current step
    step_idx = state.get("current_step", 0)
    plan = state.get("plan", [])
    
    if step_idx >= len(plan):
        # Plan completed
        return Command(goto="Finalizer")
    
    step_text = plan[step_idx]
    
    # Tool whitelist (Dynamic from Registry for Phase 4.5+)
    from .registry import get_tool_registry
    registry = get_tool_registry()
    allowed_tools = registry.list_tools()
    
    # Fallback for MVP if registry not yet populated in this process
    if not allowed_tools:
        allowed_tools = [
            "read_file", "write_file", "edit_file",
            "ls", "glob", "grep", "stat",
            "send_email"
        ]
    
    # Prompt for tool selection
    system_prompt = SystemMessage(content=(
        "You are the EXECUTOR for an AI agent system.\n"
        "Your job: Propose exactly ONE tool call to execute the current step.\n\n"
        "RULES:\n"
        "- Return ONLY valid JSON (no markdown, no explanations)\n"
        "- Use only allowed tools\n"
        "- Provide complete arguments\n"
        "- Prefer precise tools (e.g., grep before read_file for search)\n\n"
        f"ALLOWED TOOLS: {allowed_tools}\n\n"
        'FORMAT: {"name": "tool_name", "args": {...}}\n'
    ))
    
    user_prompt = HumanMessage(content=f"Execute step: {step_text}")
    
    # Invoke LLM
    response = await llm.ainvoke([system_prompt, user_prompt])
    
    # Parse with fallback
    proposed = parse_llm_json(
        str(response.content),
        fallback={"name": "", "args": {}}
    )
    
    name = proposed.get("name", "")
    args = proposed.get("args", {}) or {}
    
    # Validate tool name
    if name not in allowed_tools:
        return Command(
            update={
                "last_tool_result": {
                    "status": "failed",
                    "output": f"Tool '{name}' not allowed. Choose from: {allowed_tools}",
                    "evicted": False,
                    "size_chars": 0
                }
            },
            goto="Interpreter"
        )
    
    # Server-side validation (CRITICAL: anti-traversal, sandbox enforcement)
    is_valid, error_msg = validate_fn(name, args)
    if not is_valid:
        return Command(
            update={
                "last_tool_result": {
                    "status": "failed",
                    "output": f"Validation error: {error_msg}",
                    "evicted": False,
                    "size_chars": 0
                }
            },
            goto="Interpreter"
        )
    
    # Server-side canonicalization (ZERO-TRUST: never trust LLM hashes)
    canonical = canonicalize(args)
    args_hash = hash_fn(canonical)
    
    # Construct ProposedTool (matches Phase 3 schema)
    proposed_tool = {
        "name": name,
        "args": args,
        "canonical_args": canonical,
        "args_hash": args_hash,
        "tool_call_id": f"lc_{int(time.time() * 1000)}",
        "step_idx": step_idx,
        "created_at": time.time()
    }
    
    return Command(
        update={"proposed_tool": proposed_tool},
        goto="RiskGate"
    )


async def finalizer_node_impl(
    state: Dict[str, Any],
    llm
) -> Command[Literal["END"]]:
    """
    Finalizer Node: Generate user-facing response.
    
    Cases:
    1. awaiting_approval=True → Show APROBAR/RECHAZAR prompt
    2. awaiting_user_input=True → Show question
    3. intent="conversation" → Chat response
    4. Default → Task progress summary
    
    Output:
    - messages: [AIMessage(...)]
    """
    # Case 1: Approval pending (HITL)
    if state.get("awaiting_approval"):
        tool = state.get("proposed_tool", {})
        approval_id = state.get("approval_id", "")
        
        approval_msg = AIMessage(content=(
            "🔒 **Acción sensible requiere aprobación**\n\n"
            f"**Tool:** `{tool.get('name', 'unknown')}`\n"
            f"**Args:** `{tool.get('args', {})}`\n\n"
            "**Responde:**\n"
            f"- `APROBAR {approval_id} <TOKEN>`\n"
            f"- `RECHAZAR {approval_id}`\n"
        ))
        
        return Command(
            update={"messages": state.get("messages", []) + [approval_msg]},
            goto="END"
        )
    
    # Case 2: Need user input
    if state.get("awaiting_user_input"):
        question = state.get("question", "Necesito información adicional.")
        
        return Command(
            update={"messages": state.get("messages", []) + [AIMessage(content=question)]},
            goto="END"
        )
    
    # Case 3: Conversation intent (simple echo for MVP)
    if state.get("intent") == "conversation":
        # For MVP, just acknowledge
        # In production, could invoke LLM for real chat response
        msg = AIMessage(content="Entendido. ¿En qué más puedo ayudarte?")
        return Command(
            update={"messages": state.get("messages", []) + [msg]},
            goto="END"
        )
    
    # Case 4: Task progress summary
    plan = state.get("plan", [])
    step_status = state.get("step_status", {})
    
    if not plan:
        msg = AIMessage(content="No hay tareas en progreso.")
        return Command(
            update={"messages": state.get("messages", []) + [msg]},
            goto="END"
        )
    
    done_count = sum(1 for status in step_status.values() if status == "done")
    
    # Simple progress message (can be enhanced with LLM for richer output)
    progress_msg = f"**Progreso:** {done_count}/{len(plan)} pasos completados.\n\n"
    progress_msg += "**Pasos:**\n"
    for i, step in enumerate(plan):
        status = step_status.get(i, "pending")
        emoji = "✅" if status == "done" else "⏳" if status == "pending" else "❌"
        progress_msg += f"{emoji} {i+1}. {step}\n"
    
    return Command(
        update={"messages": state.get("messages", []) + [AIMessage(content=progress_msg)]},
        goto="END"
    )


# Export for graph wiring
__all__ = [
    "parse_llm_json",
    "planner_node_impl",
    "executor_node_impl",
    "finalizer_node_impl"
]

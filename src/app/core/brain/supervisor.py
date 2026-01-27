"""
Supervisor Node: Orchestrates plan execution with retry logic.

Responsibilities:
- Advance to next step when current step completes
- Retry failed steps (max 3 attempts)
- Terminate when plan complete or max retries exceeded
- Update tracking state (current_step, tries, step_status)

Flow:
    Supervisor → Executor → RiskGate → [Auth/Tools] → Interpreter → Supervisor (loop)
"""

from typing import Dict, Any, Literal
from langgraph.types import Command


def supervisor_node(state: Dict[str, Any]) -> Command[Literal["Executor", "Finalizer"]]:
    """
    Supervisor: Orchestrate task execution with retry logic.
    """
    step_idx = state.get("current_step", 0)
    plan = state.get("plan", [])
    step_status = state.get("step_status", {})
    tries = state.get("tries", {})
    
    # Edge case: No plan
    if not plan:
        return Command(goto="Finalizer")
    
    # Edge case: Beyond plan
    if step_idx >= len(plan):
        return Command(goto="Finalizer")
    
    current_status = step_status.get(step_idx, "pending")
    
    # Case 1: Step completed successfully
    if current_status == "done":
        next_idx = step_idx + 1
        
        # Check if plan complete
        if next_idx >= len(plan):
            return Command(goto="Finalizer")
        
        # Advance to next step
        return Command(
            update={"current_step": next_idx},
            goto="Executor"
        )
    
    # Case 2: Step failed
    if current_status == "failed":
        current_tries = tries.get(step_idx, 0)
        
        # Max retries exceeded
        if current_tries >= 3:
            return Command(
                update={
                    "awaiting_user_input": True,
                    "question": (
                        f"❌ **Paso {step_idx + 1} falló después de 3 intentos**\n\n"
                        f"**Paso:** {plan[step_idx]}\n\n"
                        "**Opciones:**\n"
                        "1. Reintenta el paso (responde 'REINTENTAR')\n"
                        "2. Omite el paso (responde 'OMITIR')\n"
                        "3. Cancela la tarea (responde 'CANCELAR')"
                    )
                },
                goto="Finalizer"
            )
        
        # Retry step
        return Command(
            update={
                "tries": {**tries, step_idx: current_tries + 1},
                # Reset step status to pending for retry
                "step_status": {**step_status, step_idx: "pending"}
            },
            goto="Executor"
        )
    
    # Case 3: Step pending (first attempt or after retry)
    # Start execution
    return Command(goto="Executor")


# Export for graph wiring
__all__ = ["supervisor_node"]

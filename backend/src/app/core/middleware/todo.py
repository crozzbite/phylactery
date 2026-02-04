"""
TodoList Middleware.

Provides tools for managing a persistent task list.
Crucial for long-running agents to track progress and plan ahead.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..backends.protocol import BackendProtocol
from ..backends.state import StateBackend


@dataclass
class Task:
    id: str
    description: str
    status: Literal["todo", "in_progress", "done", "failed"] = "todo"
    subtasks: list["Task"] = field(default_factory=list)


class TodoListMiddleware:
    """
    Middleware that manages a todo list using filesystem storage.
    
    Files are stored in /workspace/todo.md (or custom path)
    using a simple markdown format compatible with human reading.
    """

    def __init__(
        self,
        backend_factory: Callable[[Protocol], BackendProtocol] | None = None,
        todo_path: str = "/workspace/todo.md"
    ):
        self.backend_factory = backend_factory
        self.todo_path = todo_path

    def _get_backend(self, runtime: RunnableConfig) -> BackendProtocol:
        if self.backend_factory:
            return self.backend_factory(runtime)
        return StateBackend(runtime)

    def _parse_todo(self, content: str) -> list[dict[str, Any]]:
        """Simple parser for markdown todo lists."""
        # TODO: Implement robust markdown parsing
        # For now, just a placeholder that assumes simple format
        tasks = []
        for line in content.splitlines():
            if line.startswith("- [ ] "):
                tasks.append({"status": "todo", "desc": line[6:]})
            elif line.startswith("- [x] "):
                tasks.append({"status": "done", "desc": line[6:]})
        return tasks

    def get_tools(self, runtime: Protocol) -> list[Callable[..., Any]]:
        backend = self._get_backend(runtime)

        @tool
        def add_task(description: str) -> str:
            """Add a new task to the todo list."""
            try:
                # Read existing
                content = backend.read(self.todo_path)
                if content.startswith("Error"):
                    content = "# Todo List\n"
                    backend.write(self.todo_path, content)

                # Append task
                new_line = f"\n- [ ] {description}"
                if content.strip():
                    backend.write(self.todo_path, content + new_line)
                else:
                    backend.write(self.todo_path, "# Todo List" + new_line)

                return f"Added task: {description}"
            except Exception as e:
                return f"Error adding task: {e}"

        @tool
        def update_task(task_text: str, status: Literal["todo", "done"]) -> str:
            """Update task status (simple string match for now)."""
            try:
                content = backend.read(self.todo_path)
                if content.startswith("Error"):
                    return "Todo list not found"

                mark = "[x]" if status == "done" else "[ ]"
                old_mark = "[ ]" if status == "done" else "[x]"

                # Simple replace for demo purposes
                # Real implementation needs ID or fuzzy match
                old_line = f"- {old_mark} {task_text}"
                new_line = f"- {mark} {task_text}"

                res = backend.edit(self.todo_path, old_line, new_line)
                if res.error:
                    return f"Could not find task: {task_text}"
                return f"Updated task status to {status}"
            except Exception as e:
                return f"Error updating task: {e}"

        @tool
        def list_tasks() -> str:
            """Read current todo list."""
            return backend.read(self.todo_path)

        return [add_task, update_task, list_tasks]

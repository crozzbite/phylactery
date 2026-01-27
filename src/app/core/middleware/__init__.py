"""
Middleware components for Phylactery agents.

Middleware provides composable capabilities to agents:
- FilesystemMiddleware: File operations (ls, read, write, edit, glob, grep)
- TodoListMiddleware: Task planning and tracking
- EvictionMiddleware: Automatic tool result eviction
"""

from .filesystem import FilesystemMiddleware
from .todo import TodoListMiddleware
from .eviction import EvictionMiddleware

__all__ = [
    "FilesystemMiddleware",
    "TodoListMiddleware",
    "EvictionMiddleware"
]

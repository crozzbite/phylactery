"""
Backend abstraction layer for Phylactery.

Inspired by LangChain Deep Agents backends architecture.
Provides pluggable storage for filesystem operations with different persistence strategies.
"""

from .protocol import BackendProtocol, FileInfo, WriteResult, EditResult, GrepMatch
from .state import StateBackend
from .store import StoreBackend
from .composite import CompositeBackend

__all__ = [
    "BackendProtocol",
    "FileInfo",
    "WriteResult",
    "EditResult",
    "GrepMatch",
    "StateBackend",
    "StoreBackend",
    "CompositeBackend",
]

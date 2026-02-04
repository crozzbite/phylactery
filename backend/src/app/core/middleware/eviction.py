"""
Eviction Middleware.

Automatically manages context window usage by evicting large tool outputs
to the filesystem (StateBackend).

When a tool output exceeds `max_tokens`, it is replaced with a reference:
"Output too large. Saved to /workspace/evicted_files/<id>.txt"
"""

import uuid
from collections.abc import Callable
from typing import Protocol

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from ..backends.protocol import BackendProtocol
from ..backends.state import StateBackend


class EvictionMiddleware:
    """
    Middleware that intercepts tool outputs and evicts large ones to files.
    """

    def __init__(
        self,
        backend_factory: Callable[[Protocol], BackendProtocol] | None = None,
        max_chars: int = 10000,  # ~2500 tokens
        eviction_dir: str = "/workspace/evicted/"
    ):
        self.backend_factory = backend_factory
        self.max_chars = max_chars
        self.eviction_dir = eviction_dir

    def _get_backend(self, runtime: RunnableConfig) -> BackendProtocol:
        if self.backend_factory:
            return self.backend_factory(runtime)
        return StateBackend(runtime)

    def process_messages(self, messages: list[BaseMessage], runtime: object) -> list[BaseMessage]:
        """
        Scan messages and evict large tool outputs.
        Should be called before sending messages to the LLM.
        """
        backend = self._get_backend(runtime)
        processed = []

        for msg in messages:
            if isinstance(msg, ToolMessage) and len(str(msg.content)) > self.max_chars:
                # Evict content
                content_str = str(msg.content)
                file_id = str(uuid.uuid4())[:8]
                file_path = f"{self.eviction_dir}{msg.tool_call_id}_{file_id}.txt"

                # Write to backend
                backend.write(file_path, content_str)

                # Replace content
                new_content = (
                    f"⚠️ Output too large ({len(content_str)} chars). "
                    f"Evicted to {file_path}.\n"
                    f"Use `read_file('{file_path}')` to view contents."
                )

                processed.append(ToolMessage(
                    content=new_content,
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                    additional_kwargs=msg.additional_kwargs
                ))
            else:
                processed.append(msg)

        return processed

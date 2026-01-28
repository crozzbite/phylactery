"""
Idempotency Store: Prevent duplicate tool executions.

Responsibilities:
- Store tool results with TTL
- Generate idempotency keys from (thread_id, step_idx, args_hash)
- Background TTL cleanup
- Redis-ready interface (in-memory MVP)

Use Case:
    If agent crashes after tool execution but before state save,
    restarting with same thread_id will return cached result
    instead of re-executing the tool.
"""

import time
import asyncio
import hashlib
from typing import Dict, Optional
from threading import Lock


def make_idempotency_key(thread_id: str, step_idx: int, args_hash: str) -> str:
    """
    Generate idempotency key from execution context.
    
    Format: SHA256(thread_id:step_idx:args_hash)
    
    Args:
        thread_id: Conversation/thread identifier
        step_idx: Step index in plan
        args_hash: SHA256 hash of canonical args
    
    Returns:
        str: 64-character hex string
    
    Example:
        >>> key = make_idempotency_key("thread-123", 2, "abc123...")
        >>> len(key)
        64
    """
    raw = f"{thread_id}:{step_idx}:{args_hash}".encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


class IdempotencyStore:
    """
    In-memory idempotency store with TTL.
    
    Interface is Redis-compatible for future migration.
    
    Data Structure:
        {
            "idempotency_key": {
                "value": {...tool_result...},
                "expires_at": timestamp
            }
        }
    
    Background Cleanup:
        Runs every 60s to remove expired keys.
    """
    
    def __init__(self):
        """Initialize empty store with background cleanup."""
        self._store: Dict[str, Dict[str, object]] = {}
        self._lock = Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start_cleanup(self):
        """Start background TTL cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _cleanup_loop(self):
        """Background task to remove expired keys."""
        while True:
            await asyncio.sleep(60)  # Run every 60s
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """Remove expired keys (called by background task)."""
        now = time.time()
        with self._lock:
            expired_keys = [
                key for key, data in self._store.items()
                if data["expires_at"] < now
            ]
            for key in expired_keys:
                del self._store[key]
    
    def get(self, key: str) -> Optional[Dict[str, object]]:
        """
        Retrieve cached result.
        
        Args:
            key: Idempotency key
        
        Returns:
            Tool result dict or None if not found/expired
        """
        with self._lock:
            data = self._store.get(key)
            if not data:
                return None
            
            # Check expiry
            if data["expires_at"] < time.time():
                del self._store[key]
                return None
            
            return data["value"]
    
    def set(self, key: str, value: Dict[str, object], ttl: int = 600) -> None:
        """
        Store result with TTL.
        
        Args:
            key: Idempotency key
            value: Tool result to cache
            ttl: Time-to-live in seconds (default: 600 = 10 minutes)
        """
        expires_at = time.time() + ttl
        with self._lock:
            self._store[key] = {
                "value": value,
                "expires_at": expires_at
            }
    
    def clear(self) -> None:
        """Clear all cached results (useful for testing)."""
        with self._lock:
            self._store.clear()
    
    def size(self) -> int:
        """Get number of cached results."""
        with self._lock:
            return len(self._store)


# Global instance (singleton pattern for simplicity)
_global_store: Optional[IdempotencyStore] = None


def get_idempotency_store() -> IdempotencyStore:
    """
    Get global idempotency store instance.
    
    Returns:
        IdempotencyStore: Singleton instance
    """
    global _global_store
    if _global_store is None:
        _global_store = IdempotencyStore()
    return _global_store


__all__ = [
    "make_idempotency_key",
    "IdempotencyStore",
    "get_idempotency_store"
]

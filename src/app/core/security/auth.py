import hmac
import hashlib
import time
import secrets
import os
import threading
from typing import Optional

class TokenManager:
    """
    HMAC-SHA256 Token Manager for Approval Workflows.
    
    Security Model:
    - Based on RFC 2104 (HMAC)
    - Anti-replay via token consumption (OWASP)
    - Payload binding for zero-trust verification (NIST SP 800-207)
    
    CRITICAL: The 'payload' argument MUST be the canonical binding string
    that includes all context (e.g., "thread_id:user_id:approval_hash").
    DO NOT pass raw tool args or arbitrary strings.
    
    Multi-Process Warning:
    - In-memory token store (_used_tokens) is NOT safe across workers/pods.
    - For production (FastAPI with --workers N, Kubernetes), use Redis:
      Example: SETNX token 1 EX 300
    """
    
    def __init__(self, secret_key: str):
        # Strict validation for production
        is_dev = os.environ.get("ENV") in {"dev", "development", "local"}
        
        if not secret_key:
            raise ValueError("TokenManager requires a non-empty secret_key")
            
        # Prevent weak keys in non-dev environments
        if not is_dev:
            if secret_key == "dev-secret-key" or len(secret_key) < 32:
                raise ValueError(
                    "TokenManager requires a secure secret_key in production "
                    "(minimum 32 characters, use secrets.token_urlsafe(32))"
                )
        
        self.secret = secret_key.encode()
        self._used_tokens: dict[str, float] = {}  # token -> expiry_timestamp
        self._lock = threading.Lock()  # For atomic check-and-set in single process
        
    def sign_payload(self, payload: str) -> str:
        """
        Generates a cryptographically signed token for the given payload.
        
        Format: v1.timestamp.nonce.signature
        
        Args:
            payload: The canonical binding string (e.g., "thread:user:hash")
        
        Returns:
            Signed token string
        """
        if not isinstance(payload, str):
            raise TypeError("Payload must be a canonical string, not dict/object")
            
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(8)  # 16 chars of entropy
        
        # Canonical Message: timestamp:nonce:payload
        msg = f"{timestamp}:{nonce}:{payload}".encode()
        signature = hmac.new(self.secret, msg, hashlib.sha256).hexdigest()
        
        return f"v1.{timestamp}.{nonce}.{signature}"

    def verify_signature(self, token: str, payload: str, max_age_seconds: int = 300) -> bool:
        """
        Verifies token signature and expiry WITHOUT consuming it.
        Use this for read-only checks.
        
        For approval workflows, use verify_and_consume() instead.
        """
        try:
            parts = token.split('.')
            if len(parts) != 4:
                return False
            
            ver, ts, nonce, sig = parts
            if ver != "v1":
                return False
            
            # 1. Expiration Check
            try:
                ts_int = int(ts)
            except ValueError:
                return False

            if time.time() - ts_int > max_age_seconds:
                return False

            # 2. Signature Check
            msg = f"{ts}:{nonce}:{payload}".encode()
            expected_sig = hmac.new(self.secret, msg, hashlib.sha256).hexdigest()
            
            return hmac.compare_digest(sig, expected_sig)
            
        except Exception:
            return False

    def verify_and_consume(self, token: str, payload: str, max_age_seconds: int = 300) -> bool:
        """
        ATOMIC: Verifies token and marks it as used in a single operation.
        
        This is the ONLY method ApprovalHandler should use.
        
        Returns:
            True if token is valid AND not previously used
            False otherwise (invalid, expired, or replayed)
        
        Threading Safety:
            Single-process: Protected by threading.Lock
            Multi-process: NOT SAFE. Use Redis SETNX for production.
        """
        with self._lock:  # Atomic in single process
            # 1. Verify signature first (cheap operation)
            if not self.verify_signature(token, payload, max_age_seconds):
                return False
            
            # 2. Anti-Replay: Check if already used
            if token in self._used_tokens:
                # Token was already consumed
                return False
            
            # 3. Consume: Mark as used
            self._used_tokens[token] = time.time() + max_age_seconds
            
            # 4. Cleanup old tokens (basic TTL)
            self._cleanup_expired_tokens()
            
            return True
    
    def _cleanup_expired_tokens(self):
        """
        Removes expired tokens from the in-memory store.
        
        Called during verify_and_consume to prevent unbounded growth.
        In production with Redis, this is handled by TTL automatically.
        """
        now = time.time()
        # Remove tokens past their expiry
        expired = [token for token, expiry in self._used_tokens.items() if expiry < now]
        for token in expired:
            del self._used_tokens[token]
    
    def is_used(self, token: str) -> bool:
        """
        Checks if token has been consumed.
        
        WARNING: Do NOT use this in approval flow. Use verify_and_consume() instead
        to avoid race conditions.
        """
        with self._lock:
            return token in self._used_tokens

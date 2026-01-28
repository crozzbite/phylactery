"""
Configuration and helper functions for Phase 4 LLM integration.

This module provides:
- LLM factory with environment-based model selection
- Canonicalization and hashing for zero-trust verification
- Server-side validation for tool arguments (anti-traversal, sandbox enforcement)

Security Model:
- Never trust LLM-generated canonical args or hashes
- All validation happens server-side in Python (not in LLM)
- Follows OWASP path traversal prevention guidelines
"""

import os
import json
import hashlib
import re
from typing import Tuple, Dict

def get_llm():
    """
    Factory function to create LLM instance with environment-based config.
    
    Environment Variables:
    - OPENAI_API_KEY: Required
    - OPENAI_MODEL: Optional (default: gpt-4o-mini for cost efficiency)
    - OPENAI_TEMPERATURE: Optional (default: 0 for deterministic output)
    
    Returns:
        ChatOpenAI: Configured LLM instance
    
    Raises:
        ValueError: If OPENAI_API_KEY not set
    """
    from langchain_openai import ChatOpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable required. "
            "Set it with: export OPENAI_API_KEY=sk-..."
        )
    
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0"))
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        # Timeout to prevent hanging
        request_timeout=30,
        # Max retries for transient errors
        max_retries=2
    )


def canonicalize(args: Dict[str, object]) -> str:
    """
    Canonicalize tool arguments for hash calculation.
    
    Rules:
    - Sort keys alphabetically
    - JSON serialize with no whitespace
    - Deterministic output for identical args
    
    Args:
        args: Tool arguments dictionary
    
    Returns:
        str: Canonical JSON string
    
    Example:
        >>> canonicalize({"path": "file.txt", "mode": "r"})
        '{"mode":"r","path":"file.txt"}'
    """
    return json.dumps(args, sort_keys=True, separators=(',', ':'))


def calculate_hash(canonical: str) -> str:
    """
    Calculate SHA256 hash of canonical args.
    
    Args:
        canonical: Canonical JSON string from canonicalize()
    
    Returns:
        str: Hex digest (64 characters)
    
    Example:
        >>> canonical = canonicalize({"path": "test.txt"})
        >>> hash_val = calculate_hash(canonical)
        >>> len(hash_val)
        64
    """
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def validate_tool_args(name: str, args: Dict[str, object]) -> Tuple[bool, str]:
    """
    Server-side validation for tool arguments.
    
    Security Checks:
    - Path traversal prevention (filesystem tools)
    - Sandbox enforcement (phylactery-app/ prefix required)
    - Email format validation
    - Domain whitelist (configurable)
    
    Args:
        name: Tool name
        args: Tool arguments
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
        - (True, "") if valid
        - (False, "error reason") if invalid
    
    Examples:
        >>> validate_tool_args("read_file", {"path": "../etc/passwd"})
        (False, 'Path traversal blocked: ..')
        
        >>> validate_tool_args("read_file", {"path": "phylactery-app/README.md"})
        (True, '')
    """
    # Filesystem tool validation
    if name in {"read_file", "write_file", "stat", "glob", "grep", "edit_file", "ls"}:
        path = args.get("path", "")
        
        # 1. Null byte injection prevention
        if "\x00" in path:
            return False, "Null byte injection blocked"
        
        # 2. Normalize path and check for absolute/UNC paths
        norm_path = os.path.normpath(path)
        if os.isabs(norm_path) or norm_path.startswith("\\\\"):
             return False, f"Absolute or UNC paths not allowed: {path}"
        
        # 3. Traversal block (double check norm_path)
        if ".." in norm_path.split(os.sep):
            return False, "Path traversal blocked: .."

        # 4. Sandbox enforcement
        # Determine sandbox root (absolute for comparison)
        sandbox_prefix = os.getenv("PHYLACTERY_SANDBOX_PREFIX", "phylactery-app/")
        sandbox_root = os.path.abspath(sandbox_prefix)
        target_abs = os.path.abspath(norm_path)
        
        # Security: target_abs must start with sandbox_root
        if not target_abs.startswith(sandbox_root):
            return False, f"Path outside sandbox. Must be within: {sandbox_prefix}"
    
    # Email tool validation
    if name == "send_email":
        to = args.get("to", "")
        
        # Basic email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, to):
            return False, f"Invalid email format: {to}"
        
        # Optional domain whitelist
        allowed_domains = os.getenv("PHYLACTERY_ALLOWED_EMAIL_DOMAINS", "")
        if allowed_domains:
            domains = [d.strip() for d in allowed_domains.split(",")]
            if not any(to.endswith(f"@{domain}") for domain in domains):
                return False, f"Email domain not in whitelist: {allowed_domains}"
        
        # Subject/body length limits (DoS prevention)
        subject = args.get("subject", "")
        body = args.get("body", "")
        if len(subject) > 500:
            return False, "Subject too long (max 500 chars)"
        if len(body) > 50000:
            return False, "Body too long (max 50k chars)"
    
    # All checks passed
    return True, ""


def get_pinecone_client():
    """
    Factory function to create Pinecone client instance.
    Using GRPC client for better performance in batch operations.
    
    Environment Variables:
    - PINECONE_API_KEY: Required
    
    Returns:
    - PineconeGRPC: Configured client
    """
    from pinecone.grpc import PineconeGRPC
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable required.")
    return PineconeGRPC(api_key=api_key)


def get_pinecone_index_name():
    """Returns the configured Pinecone index name."""
    return os.getenv("PINECONE_INDEX_NAME") or os.getenv("PINECONE_INDEX") or "phylactery-memory"


def get_pinecone_index_host():
    """
    Returns the Pinecone index host if configured.
    Targeting by host directly avoids an extra 'describe_index' call.
    """
    return os.getenv("PINECONE_INDEX_HOST")


# Export all for easy imports
__all__ = [
    "get_llm",
    "canonicalize",
    "calculate_hash",
    "validate_tool_args",
    "get_pinecone_client"
]

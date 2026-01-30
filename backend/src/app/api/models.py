from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field

class RunStatus(str, Enum):
    """Possible states for a Phylactery Run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    APPROVAL_REQUIRED = "approval_required"

class EventType(str, Enum):
    """Allowlisted SSE event types."""
    STATE = "state"
    TOOL_PROPOSED = "tool_proposed"
    RISK_GATE = "risk_gate"
    APPROVAL_REQUIRED = "approval_required"
    MESSAGE_DELTA = "message_delta"
    FINAL = "final"
    ERROR = "error"

class RunCreate(BaseModel):
    """Schema for creating a new Run."""
    agent_name: str
    input_text: str
    thread_id: Optional[str] = None
    metadata: Dict[str, object] = Field(default_factory=dict)

class RunResponse(BaseModel):
    """Public response for a created or retrieved Run."""
    run_id: str
    agent_name: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    thread_id: Optional[str]
    owner_id: str  # Mandatory for binding

class JobEvent(BaseModel):
    """Typed event for SSE streaming."""
    event_type: EventType  # Strict allowlist
    payload: Dict[str, object]
    timestamp: datetime = Field(default_factory=datetime.now)

class IdempotencyRequest(BaseModel):
    """Schema for idempotency check."""
    idempotency_key: str

class UserSession(BaseModel):
    """Authenticated user session data."""
    sub: str = Field(..., description="Unique Google ID")
    email: Optional[str] = None
    name: Optional[str] = None
    role: str = "user"
    iat: Optional[datetime] = None
    exp: Optional[datetime] = None

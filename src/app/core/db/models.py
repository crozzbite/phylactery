from datetime import datetime
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from enum import Enum
import uuid

class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    APPROVAL_REQUIRED = "approval_required"

class EventType(str, Enum):
    STATE = "state"
    TOOL_PROPOSED = "tool_proposed"
    RISK_GATE = "risk_gate"
    APPROVAL_REQUIRED = "approval_required"
    MESSAGE_DELTA = "message_delta"
    FINAL = "final"
    ERROR = "error"

class RunDB(SQLModel, table=True):
    """Execution record for an agent run."""
    __tablename__ = "runs"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    agent_name: str = Field(index=True)
    status: RunStatus = Field(default=RunStatus.PENDING)
    owner_id: str = Field(index=True)
    thread_id: Optional[str] = Field(default=None, index=True)
    idempotency_key: Optional[str] = Field(default=None, index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    events: List["EventDB"] = Relationship(back_populates="run", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class EventDB(SQLModel, table=True):
    """Historical record of an SSE event."""
    __tablename__ = "events"
    
    id: int = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="runs.id", index=True)
    event_type: EventType = Field(index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Payload as JSON
    data: Dict[str, object] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Relationships
    run: RunDB = Relationship(back_populates="events")

class BudgetDB(SQLModel, table=True):
    """Usage tracking per user."""
    __tablename__ = "budgets"
    
    user_id: str = Field(primary_key=True)
    total_tokens: int = Field(default=0)
    total_runs: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Quota configuration
    token_limit: int = Field(default=100000) # Default 100k tokens
    
class SecurityLogDB(SQLModel, table=True):
    """Hardened archive of security events (DLP triggers, intent blocking)."""
    __tablename__ = "security_logs"
    
    id: int = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = Field(index=True)
    category: str = Field(index=True) # e.g., "DLP", "INTENT", "AUTH"
    severity: str = Field(default="INFO")
    
    # Context as JSON
    details: Dict[str, object] = Field(default_factory=dict, sa_column=Column(JSON))
    client_ip: Optional[str] = None

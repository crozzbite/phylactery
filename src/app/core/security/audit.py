import json
import time
import os
import hashlib
from datetime import datetime
from typing import Dict, Literal, TypedDict, Union, List, Optional

# Recursive JSON Type definition for better safety than Any
JSONValue = Union[str, int, float, bool, None, Dict[str, 'JSONValue'], List['JSONValue']]

AUDIT_FILE = "security_audit.jsonl"

class AuditRecord(TypedDict):
    ts: float
    event: str
    details: Dict[str, JSONValue]
    decision: str
    risk: str
    prev_hash: str
    integrity_hash: str

from ..db import async_session_maker, SecurityLogDB


class AuditLogger:
    """
    Logs security events to an immutable append-only JSONL file AND a SQL Database.
    Implements a simplified blockchain-like hash chain for integrity in the JSONL file.
    """
    
    def __init__(self, log_path: str = AUDIT_FILE):
        self.log_path = log_path
        self._last_hash = self._get_last_hash()

    def _get_last_hash(self) -> str:
        """Reads the last line of the audit log to get the previous hash."""
        if not os.path.exists(self.log_path):
            return "0" * 64 # Genesis hash
        
        try:
            with open(self.log_path, 'rb') as f:
                try:
                    lines = f.readlines()
                    if not lines:
                        return "0" * 64
                    last_line = json.loads(lines[-1].decode())
                    return last_line.get("integrity_hash", "0" * 64)
                except Exception:
                    return "ERROR_READING_LAST_HASH"
        except FileNotFoundError:
            return "0" * 64

    async def log_event(
        self, 
        event_type: str, 
        details: Dict[str, JSONValue], 
        decision: str, 
        risk_level: str,
        user_id: Optional[str] = None
    ):
        """
        Appends a signed event to the log and the database.
        """
        timestamp_float = time.time()
        now = datetime.fromtimestamp(timestamp_float)
        
        # 1. SQL Persistence (Primary)
        if user_id:
            try:
                async with async_session_maker() as session:
                    log_db = SecurityLogDB(
                        user_id=user_id,
                        category=event_type,
                        severity=risk_level,
                        details={**details, "decision": decision},
                        timestamp=now
                    )
                    session.add(log_db)
                    await session.commit()
            except Exception as e:
                # Fallback: Just log it to JSONL if DB fails
                print(f"Error logging to SQL: {e}")

        # 2. JSONL Persistence (Redundant / Hardened)
        # Construct record without hash first
        record: AuditRecord = { # type: ignore
            "ts": timestamp_float,
            "event": event_type,
            "details": details, 
            "decision": decision, 
            "risk": risk_level,
            "prev_hash": self._last_hash,
            "integrity_hash": "" # Placeholder
        }
        
        # Calculate new hash (Integrity Binding)
        record_str = json.dumps(record, sort_keys=True)
        new_hash = hashlib.sha256(record_str.encode()).hexdigest()
        
        record["integrity_hash"] = new_hash
        
        # Write to disk
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record) + "\n")
            # Update memory state
            self._last_hash = new_hash
        except Exception as e:
            print(f"Error logging to JSONL: {e}")

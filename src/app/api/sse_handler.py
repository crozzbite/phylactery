import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Dict
from sse_starlette.sse import ServerSentEvent

from src.app.core.security.dlp import DLPProcessor
from .job_manager import job_manager
from .models import RunStatus

class SSEHandler:
    """
    Handles Server-Sent Events (SSE) for agent runs.
    Ensures all outgoing text is sanitized for PII/Secrets.
    """
    
    def __init__(self) -> None:
        self.dlp = DLPProcessor()

    async def event_generator(self, run_id: str, owner_id: str) -> AsyncGenerator[ServerSentEvent, None]:
        """
        Polls for new events from the job manager and yields them as SSE.
        Includes ownership verification and egress sanitization.
        """
        last_event_idx = 0
        
        while True:
            # get_events now checks ownership internally
            try:
                all_events = await job_manager.get_events(run_id, owner_id)
            except PermissionError:
                yield ServerSentEvent(data="Unauthorized", event="error")
                break
            
            # 1. Process new events
            if len(all_events) > last_event_idx:
                new_events = all_events[last_event_idx:]
                for event in new_events:
                    # Egress Sanitization
                    sanitized_payload = self._sanitize_payload(event.payload)
                    
                    # Ensure timestamp exists (it's Optional in JobEvent)
                    ts = event.timestamp if hasattr(event, "timestamp") and event.timestamp else datetime.utcnow()
                    
                    yield ServerSentEvent(
                        data=json.dumps({
                            "type": event.event_type,
                            "payload": sanitized_payload,
                            "timestamp": ts.isoformat()
                        }),
                        event=event.event_type
                    )
                
                last_event_idx = len(all_events)
            
            # 2. Check if run is finished
            try:
                run = await job_manager.get_run(run_id, owner_id)
                if run.status in [RunStatus.COMPLETED, RunStatus.FAILED]:
                    break
            except Exception:
                # If run disappears or errors, stop streaming
                break
                
            await asyncio.sleep(0.5)  # Poll frequency

    def _sanitize_payload(self, payload: Dict[str, object]) -> Dict[str, object]:
        """Recursively sanitizes PII from response payloads."""
        sanitized = {}
        for k, v in payload.items():
            if isinstance(v, str):
                # Sanitize text
                clean_text, _ = self.dlp.sanitize_pii(v)
                sanitized[k] = clean_text
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_payload(v)
            elif isinstance(v, list):
                sanitized[k] = [
                    self._sanitize_payload(item) if isinstance(item, dict) else item 
                    for item in v
                ]
            else:
                sanitized[k] = v
        return sanitized

# Global instance
sse_handler = SSEHandler()

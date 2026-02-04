import contextvars
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from .middleware.egress_sanitizer import redact_json_secrets

# Type alias for trace event data (replaces Any)
TraceEventData = dict[str, object] | list[object] | str | int | float | bool | None

logger = logging.getLogger(__name__)


class TraceLogger:
    """
    Handles granular tracing of agent thoughts, plans, and tool executions.
    Saves traces as JSON files for audit and debugging.
    """

    def __init__(self, base_dir: str = "traces"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Thread-safe storage for current trace
        self._trace_ctx = contextvars.ContextVar("current_trace", default=None)

    @property
    def current_trace(self) -> dict[str, object] | None:
        return self._trace_ctx.get()

    def start_trace(self, trace_id: str, initial_data: dict[str, object]) -> None:
        """Start a new trace session in the current context."""
        trace_data = {
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            "start_time": time.time(),
            "events": [],
            **initial_data
        }
        self._trace_ctx.set(trace_data)

    def log_event(self, node_name: str, event_type: str, data: TraceEventData) -> None:
        """Log a specific event, redacting sensitive information."""
        trace = self.current_trace
        if not trace:
            return

        # Phase 5.3 Audit Fix: Redact secrets before logging
        safe_data = redact_json_secrets(data) if isinstance(data, (dict, list)) else data

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "node": node_name,
            "type": event_type,
            "data": safe_data
        }
        trace["events"].append(event)

    def end_trace(self, final_status: str = "success") -> None:
        """Close and save the current trace."""
        trace = self.current_trace
        if not trace:
            return

        trace["end_time"] = time.time()
        trace["duration_seconds"] = trace["end_time"] - trace["start_time"]
        trace["status"] = final_status

        trace_id = trace["trace_id"]
        file_path = self.base_dir / f"{trace_id}.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(trace, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # Don't crash the engine if logging fails
            logger.error(f"Failed to save trace {trace_id}: {e}")

        self._trace_ctx.set(None)


# Global instance
trace_logger = TraceLogger()

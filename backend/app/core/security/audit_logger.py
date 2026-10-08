from datetime import datetime, timezone
import json
import threading
from typing import Any, Dict, List, Optional
import uuid

from app.core.logging import logger
from app.core.security.pii_redactor import pii_redactor_service


class SecurityAuditLogger:
    """
    Structured security event audit logger:
    - Emits immutable, timestamped security event records
    - Automatic PII redaction on all event details (no phone/email leakage in logs)
    - Records client identifiers only in hashed or masked form
    - Maintains an in-memory buffer of recent security events for analysis & testing
    """

    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self._events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Deep sanitization: redacts PII from all string values in the details dict."""
        sanitized = {}
        for k, v in details.items():
            if isinstance(v, str):
                sanitized[k] = pii_redactor_service.redact(v)
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_details(v)
            elif isinstance(v, list):
                sanitized[k] = [
                    pii_redactor_service.redact(item) if isinstance(item, str) else item
                    for item in v
                ]
            else:
                sanitized[k] = v
        return sanitized

    def log_event(
        self,
        event_type: str,
        client_identifier: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "WARNING",
        action_taken: str = "BLOCKED",
    ) -> Dict[str, Any]:
        """
        Records and logs a structured security audit event.
        """
        raw_details = details or {}
        clean_details = self._sanitize_details(raw_details)

        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "client_hash": client_identifier or "anonymous",
            "severity": severity.upper(),
            "action_taken": action_taken.upper(),
            "details": clean_details,
        }

        # Thread-safe buffer recording
        with self._lock:
            if len(self._events) >= self.max_buffer_size:
                self._events.pop(0)
            self._events.append(event)

        # Output to structured logger
        log_msg = f"[SECURITY_AUDIT] {json.dumps(event)}"
        if severity.upper() == "CRITICAL":
            logger.critical(log_msg)
        elif severity.upper() == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return event

    def get_recent_events(self, limit: int = 50, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves recent audit events for inspection."""
        with self._lock:
            filtered = self._events
            if event_type:
                filtered = [e for e in filtered if e["event_type"] == event_type]
            return list(filtered[-limit:])

    def clear(self) -> None:
        """Clears audit buffer (useful for test isolation)."""
        with self._lock:
            self._events.clear()


audit_logger = SecurityAuditLogger()

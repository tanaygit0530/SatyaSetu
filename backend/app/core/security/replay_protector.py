import threading
import time
from typing import Dict, Optional, Tuple

from app.core.config import settings
from app.core.exceptions import SecurityViolationException
from app.core.logging import logger


class ReplayProtector:
    """
    Replay attack prevention:
    - Tracks nonces, MessageSids, or transaction tokens within an ephemeral TTL window
    - Validates request timestamp drift (rejects requests older than window or too far in the future)
    - Rejects duplicate / replayed requests
    - Automatically purges expired entries to prevent memory exhaustion
    """

    def __init__(
        self,
        window_seconds: Optional[int] = None,
        clock_skew_tolerance_seconds: int = 30,
        max_cache_size: int = 20000,
    ):
        self.window_seconds = window_seconds or settings.REPLAY_WINDOW_SECONDS
        self.clock_skew_tolerance = clock_skew_tolerance_seconds
        self.max_cache_size = max_cache_size
        # Mapping nonce -> float timestamp recorded
        self._seen_nonces: Dict[str, float] = {}
        self._lock = threading.Lock()

    def validate_timestamp_drift(
        self,
        timestamp_epoch: float,
        window_seconds: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """
        Validates whether a timestamp is within acceptable freshness boundaries.
        Rejects:
        - Timestamps older than `window_seconds` (expired)
        - Timestamps in the future beyond `clock_skew_tolerance` (clock spoofing)
        """
        now = time.time()
        window = window_seconds or self.window_seconds

        # Check future drift (clock skew)
        if timestamp_epoch > (now + self.clock_skew_tolerance):
            drift = timestamp_epoch - now
            return False, f"Timestamp is {drift:.1f}s in the future (exceeds clock skew tolerance)."

        # Check past drift (stale / replayed)
        if (now - timestamp_epoch) > window:
            age = now - timestamp_epoch
            return False, f"Timestamp is {age:.1f}s old (exceeds replay TTL window of {window}s)."

        return True, ""

    def is_replayed(
        self,
        nonce: str,
        timestamp_epoch: Optional[float] = None,
    ) -> bool:
        """
        Checks if nonce has already been seen or if timestamp has expired.
        """
        if not nonce:
            return False

        now = time.time()

        # Validate timestamp drift if provided
        if timestamp_epoch is not None:
            valid, _ = self.validate_timestamp_drift(timestamp_epoch)
            if not valid:
                return True

        with self._lock:
            # Purge expired
            self._purge_expired(now)
            return nonce in self._seen_nonces

    def record_nonce(
        self,
        nonce: str,
        timestamp_epoch: Optional[float] = None,
    ) -> None:
        """
        Records a seen nonce into memory store.
        """
        if not nonce:
            return

        now = time.time()
        ts = timestamp_epoch if timestamp_epoch is not None else now

        with self._lock:
            self._purge_expired(now)

            if len(self._seen_nonces) >= self.max_cache_size:
                # Evict oldest entry
                oldest_key = min(self._seen_nonces.keys(), key=lambda k: self._seen_nonces[k])
                del self._seen_nonces[oldest_key]

            self._seen_nonces[nonce] = ts

    def enforce_replay_protection(
        self,
        nonce: str,
        timestamp_epoch: Optional[float] = None,
    ) -> None:
        """
        Validates nonce uniqueness and timestamp drift.
        Raises SecurityViolationException if request is a replay attack.
        """
        if not nonce:
            raise SecurityViolationException("Missing required unique nonce or request ID.")

        now = time.time()

        # 1. Validate timestamp drift
        if timestamp_epoch is not None:
            valid, reason = self.validate_timestamp_drift(timestamp_epoch)
            if not valid:
                logger.warning("Replay protection rejected request: %s", reason)
                raise SecurityViolationException(f"Replay protection rejected request: {reason}")

        # 2. Check nonce uniqueness
        with self._lock:
            self._purge_expired(now)
            if nonce in self._seen_nonces:
                logger.warning("Replay attack detected: Nonce '%s' has already been processed.", nonce)
                raise SecurityViolationException(
                    f"Replay attack detected: Nonce or message ID '{nonce}' has already been processed."
                )
            self._seen_nonces[nonce] = timestamp_epoch if timestamp_epoch is not None else now

    def _purge_expired(self, current_time: float) -> None:
        """Removes nonces older than the TTL window."""
        cutoff = current_time - self.window_seconds
        expired = [k for k, ts in self._seen_nonces.items() if ts < cutoff]
        for k in expired:
            del self._seen_nonces[k]

    def reset(self) -> None:
        """Clears memory store (for test isolation)."""
        with self._lock:
            self._seen_nonces.clear()


replay_protector = ReplayProtector()

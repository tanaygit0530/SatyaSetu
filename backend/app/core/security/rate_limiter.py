import threading
import time
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.exceptions import RateLimitExceededException
from app.core.logging import logger


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter:
    - Per-phone-number limits (prevents WhatsApp abuse and spam forwarding)
    - Per-IP limits (protects API endpoints against scraping/DDoS)
    - Thread-safe sliding window algorithm
    - Automatic timestamp purging to prevent memory leaks
    """

    def __init__(
        self,
        default_phone_limit: Optional[int] = None,
        default_ip_limit: Optional[int] = None,
        window_seconds: int = 60,
    ):
        self.default_phone_limit = default_phone_limit or settings.RATE_LIMIT_PER_NUMBER_PER_MINUTE
        self.default_ip_limit = default_ip_limit or settings.RATE_LIMIT_PER_IP_PER_MINUTE
        self.window_seconds = window_seconds
        # Dict mapping key -> list of timestamp floats
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: Optional[int] = None,
    ) -> Tuple[bool, int, float]:
        """
        Records an access attempt and checks whether key is within limit.
        Returns:
            allowed: bool
            remaining: int (remaining requests allowed in current window)
            retry_after: float (seconds until oldest entry in window expires)
        """
        if not key:
            return True, limit, 0.0

        now = time.time()
        window = window_seconds or self.window_seconds

        with self._lock:
            timestamps = self._requests.get(key, [])
            cutoff = now - window
            # Filter timestamps within active sliding window
            active = [ts for ts in timestamps if ts > cutoff]

            if len(active) >= limit:
                oldest = active[0]
                retry_after = max(0.1, round((oldest + window) - now, 1))
                self._requests[key] = active
                return False, 0, retry_after

            # Allow request and record timestamp
            active.append(now)
            self._requests[key] = active
            remaining = limit - len(active)
            return True, remaining, 0.0

    def enforce_phone_rate_limit(
        self,
        phone_hash: str,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> None:
        """
        Enforces per-number rate limit based on hashed phone identifier.
        Raises RateLimitExceededException (HTTP 429) if exceeded.
        """
        max_req = limit or self.default_phone_limit
        allowed, remaining, retry_after = self.check_rate_limit(
            key=f"phone:{phone_hash}",
            limit=max_req,
            window_seconds=window_seconds,
        )
        if not allowed:
            logger.warning(
                "Phone rate limit exceeded for client hash=%s (retry_after=%.1fs)",
                phone_hash[:12] if phone_hash else "anon",
                retry_after,
            )
            raise RateLimitExceededException(
                f"Too many requests from this phone number. Please try again in {retry_after:.0f} seconds.",
                details={"retry_after": retry_after, "limit": max_req},
            )

    def enforce_ip_rate_limit(
        self,
        ip_address: str,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> None:
        """
        Enforces per-IP rate limit.
        Raises RateLimitExceededException (HTTP 429) if exceeded.
        """
        max_req = limit or self.default_ip_limit
        allowed, remaining, retry_after = self.check_rate_limit(
            key=f"ip:{ip_address}",
            limit=max_req,
            window_seconds=window_seconds,
        )
        if not allowed:
            logger.warning(
                "IP rate limit exceeded for client IP=%s (retry_after=%.1fs)",
                ip_address,
                retry_after,
            )
            raise RateLimitExceededException(
                f"Rate limit exceeded for your IP address. Please try again in {retry_after:.0f} seconds.",
                details={"retry_after": retry_after, "limit": max_req},
            )

    def reset(self) -> None:
        """Resets all rate limit windows (for testing or administrative reset)."""
        with self._lock:
            self._requests.clear()


rate_limiter = SlidingWindowRateLimiter()

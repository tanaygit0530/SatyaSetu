from datetime import datetime, timezone
import threading
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.exceptions import TokenBudgetExceededException
from app.core.logging import logger


class DailyTokenBudgetManager:
    """
    Daily model & token budget cap manager:
    - Protects backend against unbounded external LLM API costs
    - Tracks tokens per calendar day (UTC)
    - Automatically rolls over at UTC midnight
    - Enforces hard stop when daily budget cap is reached
    """

    def __init__(self, daily_budget_cap: Optional[int] = None):
        self.daily_budget_cap = daily_budget_cap or settings.DAILY_TOKEN_BUDGET
        self._current_date_str = self._get_utc_date_str()
        self._consumed_tokens = 0
        self._model_usage: Dict[str, int] = {}
        self._lock = threading.Lock()

    def _get_utc_date_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _check_and_rollover(self) -> None:
        """Internal helper: resets counter if date has changed to a new UTC day."""
        today = self._get_utc_date_str()
        if today != self._current_date_str:
            logger.info(
                "Daily token budget rollover: Previous date %s used %d tokens. Resetting for %s.",
                self._current_date_str,
                self._consumed_tokens,
                today,
            )
            self._current_date_str = today
            self._consumed_tokens = 0
            self._model_usage.clear()

    def check_budget_available(self, estimated_tokens: int = 100) -> bool:
        """
        Checks whether remaining daily budget can accommodate estimated tokens.
        """
        with self._lock:
            self._check_and_rollover()
            return (self._consumed_tokens + estimated_tokens) <= self.daily_budget_cap

    def enforce_budget(self, estimated_tokens: int = 100) -> None:
        """
        Enforces token budget availability.
        Raises TokenBudgetExceededException if budget is exhausted.
        """
        with self._lock:
            self._check_and_rollover()
            if (self._consumed_tokens + estimated_tokens) > self.daily_budget_cap:
                logger.error(
                    "Daily token budget ceiling reached: consumed=%d, cap=%d",
                    self._consumed_tokens,
                    self.daily_budget_cap,
                )
                raise TokenBudgetExceededException(
                    f"Daily LLM token budget cap of {self.daily_budget_cap:,} tokens has been reached.",
                    details={
                        "consumed": self._consumed_tokens,
                        "cap": self.daily_budget_cap,
                        "date": self._current_date_str,
                    },
                )

    def consume_tokens(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
    ) -> int:
        """
        Records consumed tokens and updates daily counter.
        Returns the new total tokens consumed today.
        """
        total = max(0, prompt_tokens) + max(0, completion_tokens)
        model_name = model or "default"

        with self._lock:
            self._check_and_rollover()
            self._consumed_tokens += total
            self._model_usage[model_name] = self._model_usage.get(model_name, 0) + total
            logger.debug(
                "Recorded %d tokens (model=%s). Daily total: %d / %d",
                total,
                model_name,
                self._consumed_tokens,
                self.daily_budget_cap,
            )
            return self._consumed_tokens

    def get_status(self) -> Dict[str, Any]:
        """Returns current daily token usage status."""
        with self._lock:
            self._check_and_rollover()
            remaining = max(0, self.daily_budget_cap - self._consumed_tokens)
            percent = round((self._consumed_tokens / max(1, self.daily_budget_cap)) * 100, 2)
            return {
                "date": self._current_date_str,
                "daily_budget_cap": self.daily_budget_cap,
                "consumed_tokens": self._consumed_tokens,
                "remaining_tokens": remaining,
                "percent_used": percent,
                "is_exhausted": self._consumed_tokens >= self.daily_budget_cap,
                "models": dict(self._model_usage),
            }

    def reset(self, new_cap: Optional[int] = None) -> None:
        """Resets the budget counter (useful for testing)."""
        with self._lock:
            if new_cap is not None:
                self.daily_budget_cap = new_cap
            self._current_date_str = self._get_utc_date_str()
            self._consumed_tokens = 0
            self._model_usage.clear()


token_budget_manager = DailyTokenBudgetManager()

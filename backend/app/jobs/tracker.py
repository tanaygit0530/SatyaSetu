from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.logging import logger
from app.repositories.check_repository import CheckRepository
from app.schemas.core import ProcessingStage
from app.schemas.enums import ProcessingStatus


def sanitize_error(exc: Union[Exception, str]) -> Tuple[str, str]:
    """
    Sanitizes raw exceptions into safe, standardized error codes and client-friendly messages.
    Guarantees that internal API keys, tokens, credentials, and raw provider traces are NEVER exposed.
    """
    err_str = str(exc).lower()

    # 1. Quota / Rate limit
    if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
        return "RATE_LIMIT_EXCEEDED", "Verification provider rate limit or quota exceeded. Please retry shortly."

    # 2. Timeout
    if "timeout" in err_str or "timed out" in err_str or "deadline" in err_str:
        return "PROVIDER_TIMEOUT", "An upstream verification retrieval provider timed out."

    # 3. Connection / DNS / Network
    if "connect" in err_str or "network" in err_str or "dns" in err_str or "unreachable" in err_str:
        return "PROVIDER_UNAVAILABLE", "Remote verification service is temporarily unreachable."

    # 4. Input formatting / payload constraints
    if "invalid" in err_str and ("format" in err_str or "input" in err_str or "magic bytes" in err_str):
        return "INVALID_INPUT_FORMAT", "The submitted input content format is invalid or unsupported."

    # 5. Empty or unverifiable content
    if "empty" in err_str or "blank" in err_str or "no content" in err_str:
        return "EMPTY_CONTENT", "The input message contains no claim-bearing text."

    # 6. SSRF / Security restrictions
    if "ssrf" in err_str or "blocked ip" in err_str or "security" in err_str:
        return "SECURITY_RESTRICTION", "The referenced URL or domain cannot be safely retrieved."

    # 7. Grounding or validation failure
    if "grounding" in err_str or "locking" in err_str:
        return "GROUNDING_VALIDATION_ERROR", "Evidence grounding validation could not be completed."

    # Default safe fallback
    return "INTERNAL_PROCESSING_ERROR", "An internal error occurred during verification processing."


class ProcessingProgressTracker:
    """
    Stateful progress tracker for an individual verification check.
    Manages transitions across the 8 canonical stages:
    RECEIVED -> EXTRACTING -> CLAIMING -> RETRIEVING -> VALIDATING -> VERIFYING -> COMPLETED / FAILED
    """

    def __init__(
        self,
        check_id: str,
        check_repo: Optional[CheckRepository] = None,
        job: Optional[Any] = None,
    ):
        self.check_id = check_id
        self.check_repo = check_repo or CheckRepository()
        self.job = job

        self.current_stage: ProcessingStatus = ProcessingStatus.RECEIVED
        self.current_status: str = "RUNNING"
        self.started_at: datetime = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.error_code: Optional[str] = None
        self.stages: List[ProcessingStage] = []
        self._stage_starts: Dict[str, datetime] = {}

    def start_stage(self, stage: Union[ProcessingStatus, str]) -> ProcessingStage:
        """
        Transitions to a new stage in RUNNING state.
        """
        st_enum = stage if isinstance(stage, ProcessingStatus) else ProcessingStatus(str(stage))
        now = datetime.now(timezone.utc)
        self.current_stage = st_enum
        self.current_status = "RUNNING"
        self._stage_starts[st_enum.value] = now

        stage_obj = ProcessingStage(
            stage=st_enum,
            status="RUNNING",
            started_at=now,
            completed_at=None,
            duration_ms=0,
            error_code=None,
        )

        # Append or replace active stage
        if self.stages and self.stages[-1].stage == st_enum and self.stages[-1].status == "RUNNING":
            self.stages[-1] = stage_obj
        else:
            self.stages.append(stage_obj)

        self._sync_job_and_repo(stage_obj)
        return stage_obj

    def complete_stage(
        self,
        stage: Union[ProcessingStatus, str],
        details: Optional[str] = None,
    ) -> ProcessingStage:
        """
        Marks an active stage as COMPLETED and records execution duration.
        """
        st_enum = stage if isinstance(stage, ProcessingStatus) else ProcessingStatus(str(stage))
        now = datetime.now(timezone.utc)
        start_t = self._stage_starts.get(st_enum.value, now)
        duration = int((now - start_t).total_seconds() * 1000)

        stage_obj = ProcessingStage(
            stage=st_enum,
            status="COMPLETED",
            started_at=start_t,
            completed_at=now,
            duration_ms=duration,
            error_code=None,
            details=details,
        )

        # Update matching stage in history
        updated = False
        for i in reversed(range(len(self.stages))):
            if self.stages[i].stage == st_enum:
                self.stages[i] = stage_obj
                updated = True
                break
        if not updated:
            self.stages.append(stage_obj)

        if st_enum == ProcessingStatus.COMPLETED:
            self.current_stage = ProcessingStatus.COMPLETED
            self.current_status = "COMPLETED"
            self.completed_at = now

        self._sync_job_and_repo(stage_obj)
        return stage_obj

    def fail_stage(
        self,
        stage: Union[ProcessingStatus, str],
        exc: Union[Exception, str],
    ) -> ProcessingStage:
        """
        Marks stage as FAILED with a sanitized error code, preventing leak of provider secrets.
        """
        st_enum = stage if isinstance(stage, ProcessingStatus) else ProcessingStatus(str(stage))
        now = datetime.now(timezone.utc)
        start_t = self._stage_starts.get(st_enum.value, now)
        duration = int((now - start_t).total_seconds() * 1000)

        err_code, safe_details = sanitize_error(exc)
        self.current_stage = ProcessingStatus.FAILED
        self.current_status = "FAILED"
        self.completed_at = now
        self.error_code = err_code

        stage_obj = ProcessingStage(
            stage=st_enum,
            status="FAILED",
            started_at=start_t,
            completed_at=now,
            duration_ms=duration,
            error_code=err_code,
            details=safe_details,
        )

        # Update matching stage in history
        updated = False
        for i in reversed(range(len(self.stages))):
            if self.stages[i].stage == st_enum:
                self.stages[i] = stage_obj
                updated = True
                break
        if not updated:
            self.stages.append(stage_obj)

        self._sync_job_and_repo(stage_obj)
        return stage_obj

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Returns JSON-compatible snapshot conforming to the spec:
        {
          "stage": "RETRIEVING",
          "status": "RUNNING",
          "started_at": "...",
          "completed_at": null,
          "duration_ms": 120,
          "error_code": null,
          "stages": [...]
        }
        """
        now = datetime.now(timezone.utc)
        curr_stage_val = self.current_stage.value if hasattr(self.current_stage, "value") else str(self.current_stage)
        stage_start = self._stage_starts.get(curr_stage_val, self.started_at)
        elapsed_ms = int((now - stage_start).total_seconds() * 1000) if not self.completed_at else int((self.completed_at - stage_start).total_seconds() * 1000)

        return {
            "check_id": self.check_id,
            "stage": curr_stage_val,
            "status": self.current_status,
            "started_at": stage_start,
            "completed_at": self.completed_at,
            "duration_ms": max(0, elapsed_ms),
            "error_code": self.error_code,
            "stages": [s.model_dump(mode="json") for s in self.stages],
        }

    def _sync_job_and_repo(self, stage_obj: ProcessingStage):
        """Syncs active state to in-memory job and CheckRepository."""
        if self.job:
            self.job.current_stage = stage_obj.stage.value if hasattr(stage_obj.stage, "value") else str(stage_obj.stage)
            self.job.status = stage_obj.status
            self.job.error = stage_obj.error_code
            if hasattr(self.job, "stages"):
                self.job.stages = self.stages

        try:
            self.check_repo.update_check_status(
                check_id=self.check_id,
                status=stage_obj.stage,
                stage=stage_obj,
            )
        except Exception as e:
            logger.debug("Progress sync note for '%s': %s", self.check_id, e)

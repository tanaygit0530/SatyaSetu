from datetime import datetime, timezone
from typing import Any, Optional, Union
from fastapi import BackgroundTasks

from app.core.logging import logger
from app.jobs.base import AbstractJobWorker, JobStatus, VerificationJob
from app.repositories.check_repository import CheckRepository
from app.schemas.core import ProcessingStage, VerificationResult
from app.schemas.enums import ProcessingStatus
from app.services.verification_orchestrator import (
    VerificationOrchestrator,
    verification_orchestrator,
)


from app.jobs.tracker import ProcessingProgressTracker, sanitize_error


class FastAPIBackgroundJobWorker(AbstractJobWorker):
    """
    FastAPI BackgroundTasks worker implementation for MVP.
    Coordinates non-blocking background verification without halting HTTP responses.
    Can be seamlessly substituted with a distributed queue (Celery, Redis Streams, Cloud Tasks).
    """

    def __init__(
        self,
        orchestrator: Optional[VerificationOrchestrator] = None,
        check_repo: Optional[CheckRepository] = None,
    ):
        self.orchestrator = orchestrator or verification_orchestrator
        self.check_repo = check_repo or CheckRepository()

    def enqueue_job(self, job: VerificationJob, **kwargs) -> str:
        """
        Enqueues job into FastAPI background tasks or executes directly if no task pool provided.
        """
        background_tasks: Optional[BackgroundTasks] = kwargs.get("background_tasks")
        if background_tasks is not None:
            background_tasks.add_task(self.execute_job, job)
            logger.info("Enqueued verification job '%s' for check '%s' to BackgroundTasks", job.job_id, job.check_id)
        else:
            # Synchronous / test fallback execution
            logger.info("Executing verification job '%s' synchronously (no BackgroundTasks pool)", job.job_id)
            self.execute_job(job)
        return job.job_id

    def execute_job(self, job: VerificationJob) -> VerificationResult:
        """
        Executes complete verification pipeline via VerificationOrchestrator,
        updating lifecycle stages and persisting outcome to CheckRepository.
        """
        tracker = ProcessingProgressTracker(
            check_id=job.check_id,
            check_repo=self.check_repo,
            job=job,
        )

        def on_progress(stage: Union[ProcessingStatus, str], status_val: str, err_val: Optional[str] = None):
            if status_val == "RUNNING":
                tracker.start_stage(stage)
            elif status_val == "COMPLETED":
                tracker.complete_stage(stage)
            elif status_val == "FAILED":
                tracker.fail_stage(stage, err_val or "Processing failed")

        try:
            # Execute verification pipeline coordinating stages
            result = self.orchestrator.verify(
                content=job.text,
                input_type=job.input_type,
                check_id=job.check_id,
                is_demo=job.is_demo,
                progress_callback=on_progress,
            )

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.current_stage = "COMPLETED"
            job.stage_status = "COMPLETED"
            job.result = result
            job.stages = tracker.stages

            # Persist result to check repository
            try:
                self.check_repo.save_verification_result(job.check_id, result)
            except Exception as e:
                logger.warning("Failed to persist result to check repository for '%s': %s", job.check_id, e)

            logger.info(
                "Completed verification job '%s' for check '%s' with overall verdict '%s'",
                job.job_id,
                job.check_id,
                result.overall_verdict,
            )
            return result

        except Exception as e:
            tracker.fail_stage(job.current_stage or ProcessingStatus.FAILED, e)
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.current_stage = "FAILED"
            job.stage_status = "FAILED"
            err_code, _ = sanitize_error(e)
            job.error_code = err_code
            job.error = err_code
            job.stages = tracker.stages

            logger.error("Verification job '%s' failed [code=%s]: %s", job.job_id, err_code, str(e), exc_info=True)
            raise

from datetime import datetime, timezone
from typing import Optional
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
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        job.current_stage = "VERIFYING"

        # Update check status to active
        try:
            self.check_repo.update_check_status(
                check_id=job.check_id,
                status=ProcessingStatus.VERIFYING,
                stage=ProcessingStage(
                    stage=ProcessingStatus.VERIFYING,
                    status="IN_PROGRESS",
                    started_at=job.started_at,
                ),
            )
        except Exception as e:
            logger.warning("Failed to record stage progression for check '%s': %s", job.check_id, e)

        try:
            # Execute verification pipeline
            result = self.orchestrator.verify(
                content=job.text,
                input_type=job.input_type,
                check_id=job.check_id,
                is_demo=job.is_demo,
            )

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.current_stage = "COMPLETED"
            job.result = result

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
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.error = str(e)
            job.current_stage = "FAILED"
            logger.error("Verification job '%s' failed: %s", job.job_id, str(e), exc_info=True)

            try:
                self.check_repo.update_check_status(
                    check_id=job.check_id,
                    status=ProcessingStatus.FAILED,
                    stage=ProcessingStage(
                        stage=ProcessingStatus.FAILED,
                        status="ERROR",
                        completed_at=job.completed_at,
                        details=str(e),
                    ),
                )
            except Exception as repo_err:
                logger.warning("Could not record failure status for '%s': %s", job.check_id, repo_err)

            raise

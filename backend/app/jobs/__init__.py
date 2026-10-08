from app.jobs.base import (
    AbstractJobWorker,
    JobStatus,
    VerificationJob,
)
from app.jobs.worker import FastAPIBackgroundJobWorker
from app.jobs.manager import VerificationJobManager
from app.jobs.tracker import ProcessingProgressTracker, sanitize_error

# Default global instance
job_manager = VerificationJobManager()

__all__ = [
    "AbstractJobWorker",
    "JobStatus",
    "VerificationJob",
    "FastAPIBackgroundJobWorker",
    "VerificationJobManager",
    "ProcessingProgressTracker",
    "sanitize_error",
    "job_manager",
]

from app.jobs.base import (
    AbstractJobWorker,
    JobStatus,
    VerificationJob,
)
from app.jobs.worker import FastAPIBackgroundJobWorker
from app.jobs.manager import VerificationJobManager

# Default global instance
job_manager = VerificationJobManager()

__all__ = [
    "AbstractJobWorker",
    "JobStatus",
    "VerificationJob",
    "FastAPIBackgroundJobWorker",
    "VerificationJobManager",
    "job_manager",
]

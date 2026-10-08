import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from fastapi import BackgroundTasks

from app.core.logging import logger
from app.jobs.base import AbstractJobWorker, JobStatus, VerificationJob
from app.jobs.worker import FastAPIBackgroundJobWorker
from app.repositories.check_repository import CheckRepository
from app.schemas.core import (
    Check,
    ClaimVerificationResult,
    Input,
    ProcessingStage,
    VerificationResult,
)
from app.schemas.enums import InputType, ProcessingStatus


class VerificationJobManager:
    """
    Coordinates creation, lifecycle management, and asynchronous execution
    of verification check jobs.
    """

    def __init__(
        self,
        worker: Optional[AbstractJobWorker] = None,
        check_repo: Optional[CheckRepository] = None,
    ):
        self.check_repo = check_repo or CheckRepository()
        self.worker = worker or FastAPIBackgroundJobWorker(check_repo=self.check_repo)
        self._jobs: Dict[str, VerificationJob] = {}

    def create_check_job(
        self,
        text: str,
        input_type: Union[InputType, str] = InputType.TEXT,
        check_id: Optional[str] = None,
        user_id: Optional[str] = None,
        is_demo: bool = False,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> VerificationJob:
        """
        Creates a new verification check, registers it in persistent storage,
        and enqueues background job for non-blocking execution.
        """
        cid = check_id or f"chk_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # Normalize input type
        if isinstance(input_type, str):
            try:
                inp_type_enum = InputType(input_type.upper())
            except ValueError:
                inp_type_enum = InputType.TEXT
        else:
            inp_type_enum = input_type

        # 1. Create root Check record
        input_obj = Input(
            input_id=f"inp_{cid}",
            input_type=inp_type_enum,
            raw_content=text,
            submitted_at=now,
        )
        check_record = Check(
            check_id=cid,
            user_id=user_id,
            input=input_obj,
            status=ProcessingStatus.RECEIVED,
            stages=[
                ProcessingStage(
                    stage=ProcessingStatus.RECEIVED,
                    status="COMPLETED",
                    started_at=now,
                    completed_at=now,
                )
            ],
            created_at=now,
            updated_at=now,
        )

        try:
            self.check_repo.create_check(check_record)
        except Exception as e:
            logger.warning("CheckRepository write warning for '%s': %s", cid, e)

        # 2. Instantiate and register VerificationJob
        job = VerificationJob(
            job_id=f"job_{cid}",
            check_id=cid,
            status=JobStatus.RECEIVED,
            input_type=inp_type_enum.value,
            text=text,
            user_id=user_id,
            is_demo=is_demo,
            created_at=now,
            current_stage="RECEIVED",
        )
        self._jobs[cid] = job

        # 3. Enqueue job via worker abstraction
        self.worker.enqueue_job(job, background_tasks=background_tasks)
        return job

    def get_check(self, check_id: str) -> Optional[Check]:
        """
        Retrieves check entity from repository or active job registry.
        """
        check = self.check_repo.get_check(check_id)
        if check:
            return check

        # Fallback to in-memory job if repository not yet flushed
        job = self._jobs.get(check_id)
        if not job:
            return None

        inp_type = InputType.TEXT
        try:
            inp_type = InputType(job.input_type.upper())
        except ValueError:
            pass

        return Check(
            check_id=job.check_id,
            user_id=job.user_id,
            input=Input(
                input_id=f"inp_{job.check_id}",
                input_type=inp_type,
                raw_content=job.text,
                submitted_at=job.created_at,
            ),
            status=ProcessingStatus(job.status.value) if job.status.value in ProcessingStatus._value2member_map_ else ProcessingStatus.RECEIVED,
            result=job.result,
            created_at=job.created_at,
            updated_at=job.completed_at or job.started_at or job.created_at,
        )

    def get_status(self, check_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns status progression summary for polling client conforming to:
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
        check = self.get_check(check_id)
        if not check:
            return None

        job = self._jobs.get(check_id)
        stages_source = (job.stages if (job and job.stages) else check.stages) or []
        last_stage = stages_source[-1] if stages_source else None

        now = datetime.now(timezone.utc)
        if last_stage:
            stage_val = last_stage.stage.value if hasattr(last_stage.stage, "value") else str(last_stage.stage)
            status_val = last_stage.status
            started_at = last_stage.started_at or check.created_at
            completed_at = last_stage.completed_at
            if completed_at:
                duration_ms = last_stage.duration_ms or int((completed_at - started_at).total_seconds() * 1000)
            else:
                duration_ms = int((now - started_at).total_seconds() * 1000) if started_at else 0
            error_code = last_stage.error_code or (job.error_code if job else None)
        else:
            stage_val = check.status.value
            status_val = "COMPLETED" if check.status == ProcessingStatus.COMPLETED else ("FAILED" if check.status == ProcessingStatus.FAILED else "RUNNING")
            started_at = check.created_at
            completed_at = check.result.completed_at if check.result else None
            duration_ms = check.result.processing_time_ms if check.result else int((now - started_at).total_seconds() * 1000)
            error_code = job.error_code if job else None

        serialized_stages = []
        for s in stages_source:
            if hasattr(s, "model_dump"):
                serialized_stages.append(s.model_dump(mode="json"))
            elif isinstance(s, dict):
                serialized_stages.append(s)

        return {
            "check_id": check_id,
            "stage": stage_val,
            "status": status_val,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": max(0, duration_ms) if duration_ms is not None else 0,
            "error_code": error_code,
            "processing_stage": stage_val,
            "stages": serialized_stages,
            "created_at": check.created_at,
            "updated_at": check.updated_at,
            "error": error_code,
        }

    def get_claims(self, check_id: str) -> Optional[List[ClaimVerificationResult]]:
        """
        Returns list of extracted/verified claims for check.
        Returns empty list if verification is still processing.
        Returns None if check does not exist.
        """
        check = self.get_check(check_id)
        if not check:
            return None
        if check.result and check.result.claims:
            return check.result.claims
        return []

    def get_evidence(self, check_id: str) -> Optional[List[Any]]:
        """
        Extracts all grounding evidence citations collected across verified claims.
        Returns None if check does not exist.
        """
        check = self.get_check(check_id)
        if not check:
            return None

        evidence_items: List[Any] = []
        seen_keys = set()

        if check.result and check.result.claims:
            for claim in check.result.claims:
                for ev in claim.evidence:
                    key = getattr(ev, "source_url", getattr(ev, "url", getattr(ev, "id", None)))
                    if key and key not in seen_keys:
                        seen_keys.add(key)
                        evidence_items.append(ev)
                    elif not key:
                        evidence_items.append(ev)

        return evidence_items

    def get_result(self, check_id: str) -> Optional[VerificationResult]:
        """
        Returns final VerificationResult if completed, else None.
        """
        check = self.get_check(check_id)
        if not check:
            return None
        return check.result

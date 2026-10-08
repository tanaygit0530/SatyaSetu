import pytest
from unittest.mock import MagicMock, patch
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.jobs.base import JobStatus, VerificationJob
from app.jobs.manager import VerificationJobManager
from app.jobs.worker import FastAPIBackgroundJobWorker
from app.main import app
from app.schemas.core import (
    ClaimVerificationResult,
    VerificationResult,
)
from app.schemas.enums import ConfidenceLevel, ProcessingStatus, Verdict


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. Job Abstraction Unit Tests
# ==============================================================================

def test_job_abstraction_models_and_lifecycle():
    """Verifies VerificationJob structure and JobStatus state transitions."""
    job = VerificationJob(
        job_id="job_001",
        check_id="chk_001",
        text="UPI will be banned tomorrow.",
        input_type="TEXT",
    )
    assert job.status == JobStatus.RECEIVED
    assert job.current_stage == "RECEIVED"
    assert job.result is None

    job.status = JobStatus.PROCESSING
    job.current_stage = "VERIFYING"
    assert job.status == JobStatus.PROCESSING

    mock_res = VerificationResult(
        check_id="chk_001",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_001",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="No ban announced.",
                evidence=[],
                rule_trace=["TIER_1_SOURCE_PRESENT"],
            )
        ],
        cache_hit=False,
        processing_time_ms=120,
    )
    job.result = mock_res
    job.status = JobStatus.COMPLETED
    assert job.status == JobStatus.COMPLETED
    assert job.result.claims[0].verdict == Verdict.FALSE


def test_job_worker_execution_and_error_handling():
    """Verifies that FastAPIBackgroundJobWorker executes jobs and catches errors."""
    mock_orchestrator = MagicMock()
    mock_res = VerificationResult(
        check_id="chk_test_worker",
        claims=[
            ClaimVerificationResult(
                claim_id="clm_001",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="Verified false.",
                evidence=[],
                rule_trace=[],
            )
        ],
        cache_hit=False,
        processing_time_ms=50,
    )
    mock_orchestrator.verify.return_value = mock_res

    worker = FastAPIBackgroundJobWorker(orchestrator=mock_orchestrator)
    job = VerificationJob(
        job_id="job_test_worker",
        check_id="chk_test_worker",
        text="UPI will be banned tomorrow.",
    )

    res = worker.execute_job(job)
    assert res.check_id == "chk_test_worker"
    assert job.status == JobStatus.COMPLETED
    assert job.result is not None

    # Error handling
    failing_orchestrator = MagicMock()
    failing_orchestrator.verify.side_effect = RuntimeError("Retrieval engine offline")
    failing_worker = FastAPIBackgroundJobWorker(orchestrator=failing_orchestrator)
    fail_job = VerificationJob(
        job_id="job_fail",
        check_id="chk_fail",
        text="Failure test",
    )
    with pytest.raises(RuntimeError):
        failing_worker.execute_job(fail_job)
    assert fail_job.status == JobStatus.FAILED
    assert fail_job.error == "INTERNAL_PROCESSING_ERROR"
    assert fail_job.error_code == "INTERNAL_PROCESSING_ERROR"


# ==============================================================================
# 2. FastAPI Endpoint Tests: POST /api/v1/checks
# ==============================================================================

def test_post_checks_returns_202_accepted(client):
    """
    POST /api/v1/checks
    ↓
    202 Accepted
    ↓
    check_id, status: RECEIVED
    """
    payload = {
        "input_type": "TEXT",
        "text": "UPI will be banned tomorrow.",
    }
    response = client.post("/api/v1/checks", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "check_id" in data
    assert data["check_id"].startswith("chk_")
    assert data["status"] == "RECEIVED"


def test_post_checks_custom_check_id(client):
    """Verifies that an explicitly provided check_id (e.g. chk_001) is preserved."""
    payload = {
        "check_id": "chk_001",
        "input_type": "TEXT",
        "text": "UPI will be banned tomorrow.",
    }
    response = client.post("/api/v1/checks", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["check_id"] == "chk_001"
    assert data["status"] == "RECEIVED"


def test_post_checks_root_alias(client):
    """Verifies that POST /checks also works seamlessly."""
    payload = {
        "input_type": "TEXT",
        "text": "LPG subsidy has been doubled.",
    }
    response = client.post("/checks", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "check_id" in data
    assert data["status"] == "RECEIVED"


# ==============================================================================
# 3. FastAPI Endpoint Tests: GET /api/v1/checks/{check_id}
# ==============================================================================

def test_get_check_404_for_unknown_id(client):
    """Verifies 404 response when querying a non-existent check."""
    response = client.get("/api/v1/checks/chk_nonexistent_999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_check_returns_details_after_submission(client):
    """Submits check and immediately queries GET /api/v1/checks/{check_id}."""
    cid = "chk_flow_001"
    submit_resp = client.post(
        "/api/v1/checks",
        json={"check_id": cid, "input_type": "TEXT", "text": "UPI will be banned tomorrow."},
    )
    assert submit_resp.status_code == 202

    get_resp = client.get(f"/api/v1/checks/{cid}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["check_id"] == cid
    assert data["text"] == "UPI will be banned tomorrow."
    assert data["status"] in ("RECEIVED", "VERIFYING", "COMPLETED")


# ==============================================================================
# 4. FastAPI Endpoint Tests: GET /api/v1/checks/{check_id}/status
# ==============================================================================

def test_get_check_status(client):
    """Verifies GET /api/v1/checks/{check_id}/status."""
    cid = "chk_status_001"
    client.post(
        "/api/v1/checks",
        json={"check_id": cid, "input_type": "TEXT", "text": "Testing status endpoint."},
    )

    resp = client.get(f"/api/v1/checks/{cid}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["check_id"] == cid
    assert "status" in data
    assert "processing_stage" in data


# ==============================================================================
# 5. FastAPI Endpoint Tests: GET /api/v1/checks/{check_id}/claims
# ==============================================================================

def test_get_check_claims(client):
    """Verifies GET /api/v1/checks/{check_id}/claims."""
    cid = "chk_claims_001"
    client.post(
        "/api/v1/checks",
        json={"check_id": cid, "input_type": "TEXT", "text": "UPI will be banned tomorrow."},
    )

    resp = client.get(f"/api/v1/checks/{cid}/claims")
    assert resp.status_code == 200
    data = resp.json()
    assert data["check_id"] == cid
    assert isinstance(data["claims"], list)


# ==============================================================================
# 6. FastAPI Endpoint Tests: GET /api/v1/checks/{check_id}/evidence
# ==============================================================================

def test_get_check_evidence(client):
    """Verifies GET /api/v1/checks/{check_id}/evidence."""
    cid = "chk_evidence_001"
    client.post(
        "/api/v1/checks",
        json={"check_id": cid, "input_type": "TEXT", "text": "UPI will be banned tomorrow."},
    )

    resp = client.get(f"/api/v1/checks/{cid}/evidence")
    assert resp.status_code == 200
    data = resp.json()
    assert data["check_id"] == cid
    assert isinstance(data["evidence"], list)


# ==============================================================================
# 7. FastAPI Endpoint Tests: GET /api/v1/checks/{check_id}/result
# ==============================================================================

def test_get_check_result_when_completed(client):
    """Verifies GET /api/v1/checks/{check_id}/result returns VerificationResult upon completion."""
    from app.jobs import job_manager

    cid = "chk_result_001"
    # Create check job
    job = job_manager.create_check_job(
        text="UPI will be banned tomorrow.",
        check_id=cid,
    )
    # Complete job with verification result
    result = VerificationResult(
        check_id=cid,
        claims=[
            ClaimVerificationResult(
                claim_id="clm_001",
                verdict=Verdict.FALSE,
                confidence=ConfidenceLevel.HIGH,
                explanation="No official shutdown announced by NPCI.",
                evidence=[],
                rule_trace=["TIER_1_SOURCE_PRESENT", "STRONG_CONTRADICTION"],
            )
        ],
        cache_hit=False,
        processing_time_ms=4210,
    )
    job_manager.check_repo.save_verification_result(cid, result)
    job.status = JobStatus.COMPLETED
    job.result = result

    resp = client.get(f"/api/v1/checks/{cid}/result")
    assert resp.status_code == 200
    data = resp.json()
    assert data["check_id"] == cid
    assert len(data["claims"]) == 1
    assert data["claims"][0]["verdict"] == "FALSE"
    assert data["claims"][0]["confidence"] == "HIGH"
    assert data["cache_hit"] is False
    assert data["processing_time_ms"] == 4210


def test_get_check_result_202_when_in_progress(client):
    """Verifies GET /api/v1/checks/{check_id}/result returns 202 Accepted when verification is still processing."""
    from app.jobs import job_manager

    cid = "chk_pending_001"
    bg_tasks = BackgroundTasks()
    job = job_manager.create_check_job(
        text="Pending check statement",
        check_id=cid,
        background_tasks=bg_tasks,
    )
    # Result has not yet completed
    job.result = None
    check = job_manager.check_repo.get_check(cid)
    if check:
        check.result = None
        job_manager.check_repo._local_checks[cid] = check

    resp = client.get(f"/api/v1/checks/{cid}/result")
    assert resp.status_code == 202
    data = resp.json()
    assert data["check_id"] == cid
    assert "status" in data


# ==============================================================================
# 8. Processing Progress Tracking & Error Sanitization Tests
# ==============================================================================

def test_progress_tracker_all_stages_lifecycle():
    """Verifies that ProcessingProgressTracker handles all 8 canonical stages with timestamps and duration."""
    from app.jobs.tracker import ProcessingProgressTracker
    from app.repositories.check_repository import CheckRepository
    from app.schemas.enums import ProcessingStatus

    repo = CheckRepository()
    tracker = ProcessingProgressTracker(check_id="chk_tracker_test", check_repo=repo)

    # 1. Test RECEIVED
    tracker.start_stage(ProcessingStatus.RECEIVED)
    snap = tracker.get_snapshot()
    assert snap["stage"] == "RECEIVED"
    assert snap["status"] == "RUNNING"
    tracker.complete_stage(ProcessingStatus.RECEIVED)

    # 2. Test EXTRACTING
    tracker.start_stage(ProcessingStatus.EXTRACTING)
    snap = tracker.get_snapshot()
    assert snap["stage"] == "EXTRACTING"
    assert snap["status"] == "RUNNING"
    tracker.complete_stage(ProcessingStatus.EXTRACTING)

    # 3. Test CLAIMING
    tracker.start_stage(ProcessingStatus.CLAIMING)
    tracker.complete_stage(ProcessingStatus.CLAIMING)

    # 4. Test RETRIEVING
    tracker.start_stage(ProcessingStatus.RETRIEVING)
    snap = tracker.get_snapshot()
    assert snap["stage"] == "RETRIEVING"
    assert snap["status"] == "RUNNING"
    tracker.complete_stage(ProcessingStatus.RETRIEVING)

    # 5. Test VALIDATING
    tracker.start_stage(ProcessingStatus.VALIDATING)
    tracker.complete_stage(ProcessingStatus.VALIDATING)

    # 6. Test VERIFYING
    tracker.start_stage(ProcessingStatus.VERIFYING)
    tracker.complete_stage(ProcessingStatus.VERIFYING)

    # 7. Test COMPLETED
    tracker.start_stage(ProcessingStatus.COMPLETED)
    tracker.complete_stage(ProcessingStatus.COMPLETED)
    final_snap = tracker.get_snapshot()
    assert final_snap["stage"] == "COMPLETED"
    assert final_snap["status"] == "COMPLETED"
    assert final_snap["completed_at"] is not None
    assert len(final_snap["stages"]) >= 7


def test_progress_tracker_failed_stage_sanitization():
    """Verifies that failing a stage records FAILED status, duration, and sanitized error code."""
    from app.jobs.tracker import ProcessingProgressTracker
    from app.repositories.check_repository import CheckRepository
    from app.schemas.enums import ProcessingStatus

    repo = CheckRepository()
    tracker = ProcessingProgressTracker(check_id="chk_fail_test", check_repo=repo)

    tracker.start_stage(ProcessingStatus.RETRIEVING)
    # Simulate an exception containing an API key or internal secret
    secret_exception = RuntimeError("Connection failed to https://api.provider.com/?key=sk-secret-key-123456789 timeout")
    stage_obj = tracker.fail_stage(ProcessingStatus.RETRIEVING, secret_exception)

    snap = tracker.get_snapshot()
    assert snap["stage"] == "FAILED"
    assert snap["status"] == "FAILED"
    assert snap["error_code"] == "PROVIDER_TIMEOUT"
    # Crucial security guarantee: raw secret key MUST NOT leak
    assert "sk-secret-key-123456789" not in str(snap)
    assert stage_obj.error_code == "PROVIDER_TIMEOUT"


def test_sanitize_error_never_leaks_secrets():
    """Exhaustive check that error sanitization protects credentials."""
    from app.jobs.tracker import sanitize_error

    # Rate limits
    code, msg = sanitize_error("HTTP 429 Too Many Requests: key=AIzaSySecretToken")
    assert code == "RATE_LIMIT_EXCEEDED"
    assert "AIzaSySecretToken" not in msg

    # Timeouts
    code, msg = sanitize_error("Gateway Timeout 504 for provider secret_host")
    assert code == "PROVIDER_TIMEOUT"
    assert "secret_host" not in msg

    # Unreachable
    code, msg = sanitize_error("DNS connect failed: internal-cluster.local:8080")
    assert code == "PROVIDER_UNAVAILABLE"
    assert "internal-cluster.local" not in msg

    # SSRF / Security
    code, msg = sanitize_error("Blocked IP 127.0.0.1 SSRF attempt")
    assert code == "SECURITY_RESTRICTION"
    assert "127.0.0.1" not in msg


def test_api_status_endpoint_returns_spec_format(client):
    """
    Verifies that polling GET /api/v1/checks/{id}/status returns the required format:
    {
      "stage": "RETRIEVING",
      "status": "RUNNING"
    }
    """
    from app.jobs import job_manager
    from app.schemas.core import ProcessingStage
    from app.schemas.enums import ProcessingStatus

    cid = "chk_spec_progress"
    bg_tasks = BackgroundTasks()
    job = job_manager.create_check_job(
        text="Test statement for stage progress",
        check_id=cid,
        background_tasks=bg_tasks,
    )

    # Set active stage to RETRIEVING with status RUNNING
    job.current_stage = "RETRIEVING"
    job.stage_status = "RUNNING"
    stage_retrieving = ProcessingStage(
        stage=ProcessingStatus.RETRIEVING,
        status="RUNNING",
    )
    job.stages = [stage_retrieving]
    check = job_manager.check_repo.get_check(cid)
    if check:
        check.status = ProcessingStatus.RETRIEVING
        check.stages = [stage_retrieving]
        job_manager.check_repo._local_checks[cid] = check

    # Poll status endpoint
    resp = client.get(f"/api/v1/checks/{cid}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["check_id"] == cid
    assert data["stage"] == "RETRIEVING"
    assert data["status"] == "RUNNING"
    assert "started_at" in data
    assert "duration_ms" in data
    assert "error_code" in data


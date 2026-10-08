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
    assert "Retrieval engine offline" in fail_job.error


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

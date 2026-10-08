import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.claim_memory_repository import ClaimMemoryRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.enums import Verdict
from app.schemas.review import ReviewItem, UserFeedbackType
from app.services.claim_memory import SharedClaimMemoryService
from app.services.feedback_service import FeedbackService, feedback_service


client = TestClient(app)


@pytest.fixture
def fresh_memory_repo():
    repo = ClaimMemoryRepository()
    repo._local_records.clear()
    return repo


@pytest.fixture
def fresh_review_repo():
    repo = ReviewRepository()
    repo._local_review_items.clear()
    repo._local_queue_items.clear()
    return repo


@pytest.fixture
def isolated_feedback_service(fresh_review_repo, fresh_memory_repo):
    memory_svc = SharedClaimMemoryService(memory_repo=fresh_memory_repo)
    return FeedbackService(
        review_repository=fresh_review_repo,
        claim_memory=memory_svc,
    )


# ==============================================================================
# 1. REVIEWITEM SCHEMA VALIDATION
# ==============================================================================

def test_review_item_schema_fields():
    """
    Verifies that ReviewItem contains all required specification fields:
    review_id, check_id, claim_id, feedback, status, created_at, reviewed_at, reviewer, resolution
    """
    now = datetime.now(timezone.utc)
    item = ReviewItem(
        review_id="rev_spec_001",
        check_id="chk_001",
        claim_id="clm_001",
        feedback="WRONG",
        status="PENDING",
        created_at=now,
        reviewed_at=None,
        reviewer=None,
        resolution=None,
    )
    assert item.review_id == "rev_spec_001"
    assert item.check_id == "chk_001"
    assert item.claim_id == "clm_001"
    assert item.feedback == "WRONG"
    assert item.status == "PENDING"
    assert item.created_at == now
    assert item.reviewed_at is None
    assert item.reviewer is None
    assert item.resolution is None


def test_review_item_feedback_values():
    """Allows CORRECT, WRONG, UNCLEAR and rejects invalid values."""
    item1 = ReviewItem(review_id="rev_1", check_id="chk_1", feedback="CORRECT")
    assert item1.feedback == "CORRECT"

    item2 = ReviewItem(review_id="rev_2", check_id="chk_2", feedback="wrong")
    assert item2.feedback == "WRONG"

    item3 = ReviewItem(review_id="rev_3", check_id="chk_3", feedback="UNCLEAR")
    assert item3.feedback == "UNCLEAR"

    with pytest.raises(ValueError):
        ReviewItem(review_id="rev_4", check_id="chk_4", feedback="INVALID_FEEDBACK")


# ==============================================================================
# 2. REST API: POST /api/v1/feedback
# ==============================================================================

def test_api_submit_feedback_specification_example():
    """
    Verifies exact spec example:
    POST /api/v1/feedback
    {
      "check_id": "chk_001",
      "claim_id": "clm_001",
      "feedback": "WRONG"
    }
    """
    resp = client.post(
        "/api/v1/feedback",
        json={
          "check_id": "chk_001",
          "claim_id": "clm_001",
          "feedback": "WRONG",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["check_id"] == "chk_001"
    assert data["claim_id"] == "clm_001"
    assert data["feedback"] == "WRONG"
    assert data["status"] == "PENDING"
    assert data["review_id"].startswith("rev_")
    assert data["reviewed_at"] is None
    assert data["reviewer"] is None
    assert data["resolution"] is None


def test_api_submit_feedback_all_supported_types():
    """Verifies feedback options: CORRECT, WRONG, UNCLEAR."""
    for fb in ["CORRECT", "WRONG", "UNCLEAR"]:
        resp = client.post(
            "/api/v1/feedback",
            json={
                "check_id": f"chk_{fb.lower()}",
                "claim_id": f"clm_{fb.lower()}",
                "feedback": fb,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["feedback"] == fb


def test_api_submit_feedback_rejects_invalid_feedback():
    """Submitting invalid feedback value returns 422 Unprocessable Entity."""
    resp = client.post(
        "/api/v1/feedback",
        json={
            "check_id": "chk_001",
            "feedback": "SOME_RANDOM_OPINION",
        },
    )
    assert resp.status_code == 422


# ==============================================================================
# 3. CRITICAL INVARIANT: NEVER DIRECTLY MODIFY SHARED CLAIM MEMORY
# ==============================================================================

def test_feedback_never_directly_modifies_shared_claim_memory(isolated_feedback_service):
    """
    CRITICAL REQUIREMENT:
    User feedback must NEVER directly modify Shared Claim Memory.

    Test scenario:
    1. A verified claim exists in Shared Claim Memory (verdict: FALSE).
    2. User submits feedback: 'WRONG' on that check/claim.
    3. Assert: Shared Claim Memory remains completely unchanged.
    """
    memory_svc = isolated_feedback_service.claim_memory
    claim_text = "UPI will be banned tomorrow."

    # 1. Store verified claim in Shared Claim Memory
    stored_rec = memory_svc.store_claim(
        claim_text=claim_text,
        verdict=Verdict.FALSE,
        confidence="HIGH",
        explanation="No official announcement of UPI ban.",
    )
    assert stored_rec is not None
    orig_verdict = stored_rec.verdict
    orig_cached_time = stored_rec.verified_at
    cache_id = stored_rec.cache_id

    # 2. User submits WRONG feedback
    review_item = isolated_feedback_service.submit_feedback(
        check_id="chk_upi_001",
        claim_id="clm_upi_001",
        feedback="WRONG",
    )
    assert review_item.status == "PENDING"

    # 3. VERIFY: Shared Claim Memory is 100% UNTOUCHED
    # Retrieve record from memory
    mem_rec = memory_svc.memory_repo.get_by_id(cache_id)
    assert mem_rec is not None
    # Verdict is still FALSE, not altered by user feedback
    assert mem_rec.verdict == orig_verdict
    assert mem_rec.verdict == Verdict.FALSE
    # Timestamps and explanation are pristine
    assert mem_rec.verified_at == orig_cached_time
    assert mem_rec.explanation == "No official announcement of UPI ban."

    # L0 exact hash lookup also still returns the pristine FALSE verdict
    lookup = memory_svc.lookup_claim(claim_text=claim_text)
    assert lookup.hit is True
    assert lookup.record.verdict == Verdict.FALSE


# ==============================================================================
# 4. PIPELINE: feedback -> review_queue -> human/admin review -> decision -> optional memory update
# ==============================================================================

def test_full_review_pipeline_without_memory_update(isolated_feedback_service):
    """
    Pipeline step 1: feedback -> review_queue
    Pipeline step 2: human review -> decision (dismiss/confirm without memory change)
    """
    # 1. Citizen feedback enqueued into review_queue
    item = isolated_feedback_service.submit_feedback(
        check_id="chk_201",
        claim_id="clm_201",
        feedback="WRONG",
    )
    review_id = item.review_id

    # Queue contains the pending item
    pending_items = isolated_feedback_service.list_review_queue(status="PENDING")
    assert any(i.review_id == review_id for i in pending_items)

    # 2. Human auditor reviews and makes decision
    resolved_item = isolated_feedback_service.apply_review_decision(
        review_id=review_id,
        reviewer="auditor_priya",
        decision="REJECTED",
        resolution="Auditor checked RBI circulars; verified claim is indeed false. Citizen feedback dismissed.",
        update_memory=False,
    )
    assert resolved_item.status == "REJECTED"
    assert resolved_item.reviewer == "auditor_priya"
    assert resolved_item.reviewed_at is not None
    assert "Auditor checked RBI" in resolved_item.resolution


def test_full_review_pipeline_with_authorized_memory_update(isolated_feedback_service):
    """
    Pipeline:
    feedback -> review_queue -> human/admin review -> decision -> optional memory update

    When human auditor confirms feedback was right and authorizes memory update,
    memory is updated strictly by the human decision.
    """
    memory_svc = isolated_feedback_service.claim_memory
    claim = "Senior citizens get 50% railway fare concession restored."

    # Pre-existing cached result
    memory_svc.store_claim(
        claim_text=claim,
        verdict=Verdict.FALSE,
        confidence="HIGH",
    )

    # User submits feedback
    item = isolated_feedback_service.submit_feedback(
        check_id="chk_rail_01",
        claim_id="clm_rail_01",
        feedback="WRONG",
    )

    # Human auditor verifies official new circular and authorizes memory update
    audited = isolated_feedback_service.apply_review_decision(
        review_id=item.review_id,
        reviewer="senior_admin_rajesh",
        decision="OVERTURNED",
        resolution="New Ministry circular officially restores concession. Overturning verdict to VERIFIED.",
        update_memory=True,
        new_verdict=Verdict.VERIFIED,
        claim_text=claim,
    )
    assert audited.status == "OVERTURNED"
    assert audited.reviewer == "senior_admin_rajesh"

    # Shared Claim Memory is updated ONLY following human review
    lookup = memory_svc.lookup_claim(claim_text=claim)
    assert lookup.hit is True
    assert lookup.record.verdict == Verdict.VERIFIED


# ==============================================================================
# 5. REST API REVIEW QUEUE ENDPOINTS
# ==============================================================================

def test_api_review_queue_management_endpoints():
    """Tests GET /api/v1/feedback/reviews and POST /api/v1/feedback/reviews/{id}/decision."""
    # 1. Create feedback via API
    create_resp = client.post(
        "/api/v1/feedback",
        json={
            "check_id": "chk_api_test",
            "claim_id": "clm_api_test",
            "feedback": "UNCLEAR",
        },
    )
    assert create_resp.status_code == 201
    review_id = create_resp.json()["review_id"]

    # 2. Get review item by ID
    get_resp = client.get(f"/api/v1/feedback/reviews/{review_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["review_id"] == review_id
    assert get_resp.json()["feedback"] == "UNCLEAR"

    # 3. List review queue
    list_resp = client.get("/api/v1/feedback/reviews")
    assert list_resp.status_code == 200
    assert isinstance(list_resp.json(), list)
    assert any(i["review_id"] == review_id for i in list_resp.json())

    # 4. Human auditor applies decision
    decision_resp = client.post(
        f"/api/v1/feedback/reviews/{review_id}/decision",
        json={
            "reviewer": "auditor_vikram",
            "decision": "RESOLVED",
            "resolution": "Clarified explanation language in knowledge repository.",
            "update_claim_memory": False,
        },
    )
    assert decision_resp.status_code == 200
    dec_data = decision_resp.json()
    assert dec_data["status"] == "RESOLVED"
    assert dec_data["reviewer"] == "auditor_vikram"
    assert dec_data["reviewed_at"] is not None

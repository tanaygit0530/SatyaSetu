from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import patch
import pytest

from app.core.config import settings
from app.core.database import (
    FirestoreCollections,
    get_firestore_client,
    reset_firestore_client,
    set_firestore_client,
)
from app.core.exceptions import FirebaseConfigurationError
from app.repositories import (
    CheckRepository,
    ClaimMemoryRepository,
    ClaimRepository,
    EvidenceRepository,
    FeedbackRepository,
    MetricsRepository,
    ReviewRepository,
)
from app.schemas.core import (
    CacheRecord,
    Check,
    Claim,
    ClaimResult,
    ConfidenceLevel,
    EvaluationRun,
    Evidence,
    Feedback,
    FeedbackType,
    Input,
    InputType,
    MetricRecord,
    ProcessingStage,
    ProcessingStatus,
    ReviewQueueItem,
    Verdict,
    VerificationResult,
)


# ==============================================================================
# In-Memory Mock Firestore Client for Testing
# ==============================================================================

class MockDocumentSnapshot:
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]]):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        return dict(self._data) if self._data is not None else None


class MockDocumentReference:
    def __init__(self, collection: "MockCollectionReference", doc_id: str):
        self.collection = collection
        self.id = doc_id

    def set(self, data: Dict[str, Any]):
        self.collection.storage[self.id] = dict(data)

    def get(self) -> MockDocumentSnapshot:
        if self.id in self.collection.storage:
            return MockDocumentSnapshot(self.id, self.collection.storage[self.id])
        return MockDocumentSnapshot(self.id, None)

    def update(self, update_fields: Dict[str, Any]):
        if self.id not in self.collection.storage:
            raise KeyError(f"Document {self.id} does not exist.")
        self.collection.storage[self.id].update(update_fields)

    def delete(self):
        self.collection.storage.pop(self.id, None)


class MockQuery:
    def __init__(self, collection: "MockCollectionReference", filters: Optional[List[tuple]] = None, limit_num: Optional[int] = None):
        self.collection = collection
        self.filters = filters or []
        self.limit_num = limit_num

    def where(self, field: str, op: str, value: Any) -> "MockQuery":
        new_filters = list(self.filters)
        new_filters.append((field, op, value))
        return MockQuery(self.collection, new_filters, self.limit_num)

    def limit(self, num: int) -> "MockQuery":
        return MockQuery(self.collection, self.filters, num)

    def stream(self):
        matches = []
        for doc_id, doc_data in self.collection.storage.items():
            match = True
            for field, op, val in self.filters:
                doc_val = doc_data.get(field)
                if op == "==" and doc_val != val:
                    match = False
                    break
            if match:
                matches.append(MockDocumentSnapshot(doc_id, doc_data))
        if self.limit_num is not None:
            matches = matches[: self.limit_num]
        return iter(matches)


class MockCollectionReference:
    def __init__(self, name: str):
        self.name = name
        self.storage: Dict[str, Dict[str, Any]] = {}

    def document(self, doc_id: str) -> MockDocumentReference:
        return MockDocumentReference(self, doc_id)

    def where(self, field: str, op: str, value: Any) -> MockQuery:
        return MockQuery(self).where(field, op, value)

    def limit(self, num: int) -> MockQuery:
        return MockQuery(self).limit(num)

    def stream(self):
        return MockQuery(self).stream()


class MockFirestoreClient:
    def __init__(self):
        self.collections: Dict[str, MockCollectionReference] = {}

    def collection(self, name: str) -> MockCollectionReference:
        if name not in self.collections:
            self.collections[name] = MockCollectionReference(name)
        return self.collections[name]


@pytest.fixture
def mock_firestore():
    """Provides an isolated mock Firestore client for test fixtures."""
    return MockFirestoreClient()


# ==============================================================================
# 1. Configuration Error when Firebase is Unavailable
# ==============================================================================

def test_firebase_unavailable_raises_configuration_error():
    """Verifies that accessing Firestore when unconfigured returns a clear configuration error."""
    reset_firestore_client()
    with patch.object(settings, "FIREBASE_PROJECT_ID", None), \
         patch.object(settings, "FIREBASE_CREDENTIALS_PATH", None), \
         patch.object(settings, "FIREBASE_CREDENTIALS_JSON", None):

        with pytest.raises(FirebaseConfigurationError) as exc_info:
            get_firestore_client()

        assert "Firebase is unavailable" in str(exc_info.value.message)
        assert exc_info.value.code == "FIREBASE_UNAVAILABLE"
        assert exc_info.value.status_code == 503


def test_repository_without_db_raises_configuration_error_when_unconfigured():
    """Verifies that initializing a repository without db raises FirebaseConfigurationError if env is unset."""
    reset_firestore_client()
    with patch.object(settings, "FIREBASE_PROJECT_ID", None), \
         patch.object(settings, "FIREBASE_CREDENTIALS_PATH", None), \
         patch.object(settings, "FIREBASE_CREDENTIALS_JSON", None):

        repo = CheckRepository()
        with pytest.raises(FirebaseConfigurationError):
            _ = repo.collection


# ==============================================================================
# 2. CheckRepository Tests
# ==============================================================================

def test_check_repository_lifecycle(mock_firestore):
    repo = CheckRepository(db=mock_firestore)

    check_input = Input(
        input_id="inp_01",
        input_type=InputType.TEXT,
        raw_content="PM scholarship launched for 2026",
    )
    new_check = Check(
        check_id="SC-2026-001",
        input=check_input,
        status=ProcessingStatus.RECEIVED,
    )

    # 1. create_check
    created = repo.create_check(new_check)
    assert created.check_id == "SC-2026-001"
    assert created.status == ProcessingStatus.RECEIVED

    # 2. get_check
    fetched = repo.get_check("SC-2026-001")
    assert fetched is not None
    assert fetched.check_id == "SC-2026-001"
    assert fetched.input.raw_content == "PM scholarship launched for 2026"

    # 3. update_check_status with stage progression
    stage = ProcessingStage(stage=ProcessingStatus.EXTRACTING, status="COMPLETED", duration_ms=120)
    updated = repo.update_check_status("SC-2026-001", ProcessingStatus.EXTRACTING, stage=stage)
    assert updated is not None
    assert updated.status == ProcessingStatus.EXTRACTING
    assert len(updated.stages) == 1
    assert updated.stages[0].stage == ProcessingStatus.EXTRACTING

    # 4. save_verification_result
    v_res = VerificationResult(
        result_id="res_01",
        check_id="SC-2026-001",
        overall_verdict=Verdict.VERIFIED,
        summary="Verified by Gazette of India",
        claim_results=[
            ClaimResult(
                claim_id="clm_01",
                verdict=Verdict.VERIFIED,
                confidence=ConfidenceLevel.HIGH,
                explanation="Matches Gazette circular",
            )
        ],
    )
    final_check = repo.save_verification_result("SC-2026-001", v_res)
    assert final_check is not None
    assert final_check.status == ProcessingStatus.COMPLETED
    assert final_check.result.overall_verdict == Verdict.VERIFIED

    # 5. list_checks
    checks_list = repo.list_checks(status=ProcessingStatus.COMPLETED)
    assert len(checks_list) == 1

    # 6. delete_check
    assert repo.delete_check("SC-2026-001") is True
    assert repo.get_check("SC-2026-001") is None


# ==============================================================================
# 3. ClaimRepository Tests
# ==============================================================================

def test_claim_repository_operations(mock_firestore):
    repo = ClaimRepository(db=mock_firestore)

    claim1 = Claim(
        claim_id="clm_001",
        text="The government launched scheme X in 2025.",
        language="en",
        normalized_claim="The government launched scheme X in 2025.",
        entities=["government", "scheme X"],
        dates=["2025"],
        numbers=[2025],
    )
    claim2 = Claim(
        claim_id="clm_002",
        text="Students receive ₹50,000 cash grant.",
        language="en",
        normalized_claim="Students receive ₹50,000 cash grant.",
        entities=["Students"],
        numbers=[50000],
    )

    # 1. save_claim
    saved1 = repo.save_claim(claim1, check_id="SC-2026-001")
    assert saved1.claim_id == "clm_001"

    # 2. save_claims batch
    saved_batch = repo.save_claims([claim2], check_id="SC-2026-001")
    assert len(saved_batch) == 1

    # 3. get_claim
    fetched = repo.get_claim("clm_001")
    assert fetched is not None
    assert fetched.text == "The government launched scheme X in 2025."
    assert fetched.numbers == [2025]

    # 4. get_claims_by_check_id
    check_claims = repo.get_claims_by_check_id("SC-2026-001")
    assert len(check_claims) == 2

    # 5. delete_claim
    assert repo.delete_claim("clm_001") is True
    assert repo.get_claim("clm_001") is None


# ==============================================================================
# 4. EvidenceRepository Tests
# ==============================================================================

def test_evidence_repository_operations(mock_firestore):
    repo = EvidenceRepository(db=mock_firestore)

    ev = Evidence(
        evidence_id="ev_001",
        source_url="https://example.gov.in/page",
        title="Official announcement",
        publisher="Government Department",
        source_tier=1,
        published_date="2025-06-01",
        retrieved_at="2026-10-07T12:00:00Z",
        exact_quote="Department announces scheme X.",
    )

    # 1. save_evidence
    saved = repo.save_evidence(ev)
    assert saved.evidence_id == "ev_001"

    # 2. get_evidence
    fetched = repo.get_evidence("ev_001")
    assert fetched is not None
    assert fetched.source_tier == 1
    assert fetched.publisher == "Government Department"

    # 3. get_evidence_by_url
    by_url = repo.get_evidence_by_url("https://example.gov.in/page")
    assert by_url is not None
    assert by_url.evidence_id == "ev_001"

    # 4. get_evidence_multi
    multi = repo.get_evidence_multi(["ev_001", "nonexistent"])
    assert len(multi) == 1

    # 5. list_evidence
    tier1_items = repo.list_evidence(tier=1)
    assert len(tier1_items) == 1

    # 6. delete_evidence
    assert repo.delete_evidence("ev_001") is True
    assert repo.get_evidence("ev_001") is None


# ==============================================================================
# 5. FeedbackRepository Tests
# ==============================================================================

def test_feedback_repository_operations(mock_firestore):
    repo = FeedbackRepository(db=mock_firestore)

    fb = Feedback(
        feedback_id="fb_101",
        check_id="SC-2026-001",
        feedback_type=FeedbackType.DISPUTE,
        comments="Official gazette had an amendment circular.",
        counter_evidence_urls=["https://example.gov.in/amendment"],
    )

    # 1. create_feedback
    created = repo.create_feedback(fb)
    assert created.feedback_id == "fb_101"

    # 2. get_feedback
    fetched = repo.get_feedback("fb_101")
    assert fetched is not None
    assert fetched.feedback_type == FeedbackType.DISPUTE

    # 3. get_feedback_by_check_id
    by_check = repo.get_feedback_by_check_id("SC-2026-001")
    assert len(by_check) == 1

    # 4. list_feedback
    all_fb = repo.list_feedback()
    assert len(all_fb) == 1


# ==============================================================================
# 6. ClaimMemoryRepository Tests
# ==============================================================================

def test_claim_memory_repository_operations(mock_firestore):
    repo = ClaimMemoryRepository(db=mock_firestore)

    rec = CacheRecord(
        cache_id="cch_001",
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        canonical_claim="Government launched scheme X.",
        verdict=Verdict.VERIFIED,
        verification_result_id="res_01",
        hit_count=1,
    )

    # 1. save_record
    saved = repo.save_record(rec)
    assert saved.cache_id == "cch_001"

    # 2. get_by_hash
    by_hash = repo.get_by_hash("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    assert by_hash is not None
    assert by_hash.verdict == Verdict.VERIFIED

    # 3. increment_hit_count
    updated = repo.increment_hit_count("cch_001")
    assert updated is not None
    assert updated.hit_count == 2

    # 4. delete_record
    assert repo.delete_record("cch_001") is True
    assert repo.get_by_id("cch_001") is None


# ==============================================================================
# 7. ReviewRepository Tests
# ==============================================================================

def test_review_repository_operations(mock_firestore):
    repo = ReviewRepository(db=mock_firestore)

    item = ReviewQueueItem(
        review_id="rev_001",
        check_id="SC-2026-001",
        status="PENDING",
        priority="HIGH",
        reason="DISPUTE",
    )

    # 1. create_review_item
    created = repo.create_review_item(item)
    assert created.review_id == "rev_001"

    # 2. get_review_item
    fetched = repo.get_review_item("rev_001")
    assert fetched is not None
    assert fetched.priority == "HIGH"

    # 3. update_review_status
    updated = repo.update_review_status(
        "rev_001",
        status="RESOLVED",
        auditor_notes="Confirmed amendment is valid.",
        assigned_to="auditor_42",
    )
    assert updated is not None
    assert updated.status == "RESOLVED"
    assert updated.assigned_to == "auditor_42"

    # 4. list_pending_reviews
    pending = repo.list_pending_reviews()
    assert len(pending) == 0  # because status was changed to RESOLVED

    # 5. delete_review_item
    assert repo.delete_review_item("rev_001") is True
    assert repo.get_review_item("rev_001") is None


# ==============================================================================
# 8. MetricsRepository Tests
# ==============================================================================

def test_metrics_repository_operations(mock_firestore):
    repo = MetricsRepository(db=mock_firestore)

    metric = MetricRecord(
        metric_id="met_001",
        metric_name="verification_latency_ms",
        value=342.5,
        dimensions={"input_type": "TEXT", "verdict": "VERIFIED"},
    )
    eval_run = EvaluationRun(
        run_id="run_001",
        benchmark_name="pib_official_dataset_v1",
        accuracy=0.985,
        sample_count=200,
        status="COMPLETED",
    )

    # 1. record_metric
    saved_metric = repo.record_metric(metric)
    assert saved_metric.metric_id == "met_001"

    # 2. get_metrics
    metrics = repo.get_metrics(metric_name="verification_latency_ms")
    assert len(metrics) == 1
    assert metrics[0].value == 342.5

    # 3. record_evaluation_run
    saved_run = repo.record_evaluation_run(eval_run)
    assert saved_run.run_id == "run_001"

    # 4. get_evaluation_run
    fetched_run = repo.get_evaluation_run("run_001")
    assert fetched_run is not None
    assert fetched_run.accuracy == 0.985

    # 5. list_evaluation_runs
    runs = repo.list_evaluation_runs()
    assert len(runs) == 1

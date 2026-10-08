from typing import Any, Dict, List, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError, FirebaseConfigurationError
from app.core.logging import logger
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import EvaluationRun, MetricRecord


class MetricsRepository(BaseFirestoreRepository):
    """Repository handling system metrics and benchmark evaluation runs."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.METRICS, db=db)
        self._local_metrics: List[MetricRecord] = []
        self._local_evaluations: List[EvaluationRun] = []

    @property
    def evaluation_collection(self):
        """Returns the Firestore CollectionReference for evaluation runs."""
        try:
            return self.db.collection(FirestoreCollections.EVALUATION_RUNS)
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to access collection '{FirestoreCollections.EVALUATION_RUNS}': {str(e)}"
            ) from e

    def record_metric(self, metric: Union[MetricRecord, Dict[str, Any]]) -> MetricRecord:
        """
        Saves a metric measurement into the metrics collection.
        """
        m_obj = metric if isinstance(metric, MetricRecord) else MetricRecord.model_validate(metric)
        self._local_metrics.append(m_obj)
        data = self.serialize_model(m_obj)
        try:
            doc_ref = self.collection.document(m_obj.metric_id)
            doc_ref.set(data)
            return m_obj
        except FirebaseConfigurationError:
            return m_obj
        except Exception as e:
            logger.warning("Could not persist metric to Firestore: %s", e)
            return m_obj

    def get_metrics(
        self,
        metric_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[MetricRecord]:
        """
        Retrieves recent telemetry metrics, optionally filtered by metric_name.
        """
        try:
            query = self.collection
            if metric_name is not None:
                query = query.where("metric_name", "==", metric_name)
            docs = query.limit(limit).stream()
            results: List[MetricRecord] = []
            for doc in docs:
                results.append(MetricRecord.model_validate(doc.to_dict()))
            return results
        except (FirebaseConfigurationError, Exception) as e:
            matched = [
                m for m in self._local_metrics
                if metric_name is None or m.metric_name == metric_name
            ]
            return matched[:limit]

    def record_evaluation_run(
        self,
        run: Union[EvaluationRun, Dict[str, Any]],
    ) -> EvaluationRun:
        """
        Saves a benchmark evaluation run record into the evaluation_runs collection.
        """
        run_obj = run if isinstance(run, EvaluationRun) else EvaluationRun.model_validate(run)
        self._local_evaluations.append(run_obj)
        data = self.serialize_model(run_obj)
        try:
            doc_ref = self.evaluation_collection.document(run_obj.run_id)
            doc_ref.set(data)
            return run_obj
        except FirebaseConfigurationError:
            return run_obj
        except Exception as e:
            logger.warning("Could not persist evaluation run to Firestore: %s", e)
            return run_obj

    def get_evaluation_run(self, run_id: str) -> Optional[EvaluationRun]:
        """
        Retrieves an evaluation run by run_id.
        """
        for r in self._local_evaluations:
            if r.run_id == run_id:
                return r
        try:
            doc_ref = self.evaluation_collection.document(run_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            return EvaluationRun.model_validate(doc.to_dict())
        except (FirebaseConfigurationError, Exception) as e:
            return None

    def list_evaluation_runs(self, limit: int = 20) -> List[EvaluationRun]:
        """
        Lists recent evaluation experiments.
        """
        try:
            docs = self.evaluation_collection.limit(limit).stream()
            results: List[EvaluationRun] = []
            for doc in docs:
                results.append(EvaluationRun.model_validate(doc.to_dict()))
            return results
        except (FirebaseConfigurationError, Exception) as e:
            return self._local_evaluations[:limit]

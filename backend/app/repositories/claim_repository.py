from typing import Any, Dict, List, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import Claim


class ClaimRepository(BaseFirestoreRepository):
    """Repository handling persistence for extracted atomic factual claims."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.CLAIMS, db=db)

    def save_claim(
        self,
        claim: Union[Claim, Dict[str, Any]],
        check_id: Optional[str] = None,
    ) -> Claim:
        """
        Persists an atomic claim document using claim_id as the document key.
        """
        claim_obj = claim if isinstance(claim, Claim) else Claim.model_validate(claim)
        data = self.serialize_model(claim_obj)
        if check_id:
            data["check_id"] = check_id

        try:
            doc_ref = self.collection.document(claim_obj.claim_id)
            doc_ref.set(data)
            return claim_obj
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to save claim '{claim_obj.claim_id}': {str(e)}"
            ) from e

    def save_claims(
        self,
        claims: List[Union[Claim, Dict[str, Any]]],
        check_id: Optional[str] = None,
    ) -> List[Claim]:
        """
        Saves a batch of atomic claims.
        """
        saved: List[Claim] = []
        for c in claims:
            saved.append(self.save_claim(c, check_id=check_id))
        return saved

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        """
        Retrieves a claim by its claim_id. Returns None if absent.
        """
        try:
            doc_ref = self.collection.document(claim_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            # Remove any metadata fields not in schema before validation if necessary
            data.pop("check_id", None)
            return Claim.model_validate(data)
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to retrieve claim '{claim_id}': {str(e)}"
            ) from e

    def get_claims_by_check_id(self, check_id: str) -> List[Claim]:
        """
        Queries all claims associated with a given check ID.
        """
        try:
            query = self.collection.where("check_id", "==", check_id)
            docs = query.stream()
            results: List[Claim] = []
            for doc in docs:
                data = doc.to_dict()
                data.pop("check_id", None)
                results.append(Claim.model_validate(data))
            return results
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to retrieve claims for check '{check_id}': {str(e)}"
            ) from e

    def delete_claim(self, claim_id: str) -> bool:
        """
        Deletes a claim document by its ID.
        """
        try:
            doc_ref = self.collection.document(claim_id)
            doc_ref.delete()
            return True
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to delete claim '{claim_id}': {str(e)}"
            ) from e

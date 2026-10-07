from fastapi import APIRouter, status
from app.schemas.verification import VerificationRequest, VerificationResponse
from app.services.verification_service import verification_service

router = APIRouter(prefix="/checks", tags=["Verification"])


@router.post("", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
async def submit_check(request: VerificationRequest) -> VerificationResponse:
    """
    Submits a citizen message, forwarded link, or media transcript for verification.
    Decomposes atomic claims, queries statutory registries, and computes deterministic verdict.
    """
    return await verification_service.verify_forward(request)


@router.get("/{check_id}", response_model=VerificationResponse)
async def get_check(check_id: str) -> VerificationResponse:
    """
    Retrieves an existing verified dossier by case ID.
    """
    return await verification_service.get_check_by_id(check_id)

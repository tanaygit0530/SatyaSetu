from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_current_user
from app.jobs import job_manager
from app.schemas.check import CheckDetailResponse
from app.schemas.core import User

router = APIRouter(prefix="/users", tags=["Citizen Profile & Personal Analytics"])


@router.get(
    "/me/analytics",
    status_code=status.HTTP_200_OK,
    summary="Get authenticated citizen's personal verification analytics",
    description="Returns personal metrics, verdict distributions, and timeline activity calculated strictly from the user's genuine verification records.",
)
async def get_my_analytics(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    summary = job_manager.check_repo.get_user_analytics_summary(user_id=current_user.user_id)
    return {
        "user_id": current_user.user_id,
        "phone_number": current_user.phone_number,
        **summary,
    }


@router.get(
    "/me/checks",
    response_model=List[CheckDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="List authenticated citizen's verification history",
    description="Returns verification dossiers submitted by this user, ordered by newest first.",
)
async def get_my_checks(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    verdict: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
) -> List[CheckDetailResponse]:
    checks = job_manager.check_repo.list_checks(
        user_id=current_user.user_id,
        limit=limit,
        status=status,
    )

    results: List[CheckDetailResponse] = []
    for check in checks:
        if verdict and check.result:
            v_str = str(check.result.overall_verdict.value if hasattr(check.result.overall_verdict, "value") else (check.result.overall_verdict or "")).upper()
            if verdict.upper() not in v_str:
                continue

        claims = check.result.claims if (check.result and check.result.claims) else []
        results.append(
            CheckDetailResponse(
                check_id=check.check_id,
                status=check.status.value if hasattr(check.status, "value") else str(check.status),
                input_type=check.input.input_type.value if hasattr(check.input.input_type, "value") else str(check.input.input_type),
                text=check.input.raw_content,
                created_at=check.created_at,
                updated_at=check.updated_at,
                completed_at=check.result.completed_at if check.result else None,
                claims=claims,
                result=check.result,
            )
        )

    return results

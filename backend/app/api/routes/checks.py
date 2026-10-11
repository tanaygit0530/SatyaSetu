from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from app.jobs import job_manager
from app.schemas.check import (
    CheckClaimsResponse,
    CheckCreateRequest,
    CheckCreateResponse,
    CheckDetailResponse,
    CheckEvidenceResponse,
    CheckStatusResponse,
)
from app.schemas.core import VerificationResult
from app.schemas.enums import InputType, ProcessingStatus

router = APIRouter(prefix="/checks", tags=["Verification Checks & Asynchronous Jobs"])
check_alias_router = APIRouter(prefix="/check", tags=["Verification Checks & Asynchronous Jobs"])


@check_alias_router.post(
    "",
    summary="Submit citizen check (singular /check alias)",
    description="Submits check. When ?sync=true is set, runs full pipeline synchronously and returns VerificationResult.",
)
async def submit_check_singular(
    payload: CheckCreateRequest,
    background_tasks: BackgroundTasks,
    sync: bool = False,
):
    if sync:
        from app.services.verification_orchestrator import verification_orchestrator
        text_content = payload.text or payload.content or ""
        in_type = payload.input_type.value if hasattr(payload.input_type, "value") else str(payload.input_type)
        return verification_orchestrator.verify(
            content=text_content,
            input_type=in_type,
            check_id=payload.check_id,
            is_demo=payload.is_demo,
        )
    return await submit_check(payload=payload, background_tasks=background_tasks)


@router.post(
    "",
    response_model=CheckCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit citizen check for non-blocking asynchronous verification",
    description=(
        "Enqueues a new claim verification check into the background job worker. "
        "Returns 202 Accepted immediately with check_id and status 'RECEIVED' without blocking."
    ),
)
async def submit_check(
    payload: CheckCreateRequest,
    background_tasks: BackgroundTasks,
) -> CheckCreateResponse:
    """
    POST /checks
    ↓
    202 Accepted
    ↓
    check_id
    ↓
    background processing
    """
    job = job_manager.create_check_job(
        text=payload.text or payload.content or "",
        input_type=payload.input_type,
        check_id=payload.check_id,
        user_id=payload.user_id,
        is_demo=payload.is_demo,
        background_tasks=background_tasks,
    )
    return CheckCreateResponse(
        check_id=job.check_id,
        status="RECEIVED",
    )


@router.post(
    "/upload",
    response_model=CheckCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload media attachment (screenshot, voice, PDF) and enqueue check",
    description="Ingests uploaded media via OCR/STT/PDF service, extracts text, and enqueues verification job.",
)
async def upload_and_check(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Uploaded screenshot image, voice audio, or PDF notice"),
    input_type: str = Form("SCREENSHOT", description="Type of input: SCREENSHOT, VOICE, PDF"),
) -> CheckCreateResponse:
    contents = await file.read()
    extracted_text = ""
    norm_type = input_type.upper()

    if norm_type in ("SCREENSHOT", "IMAGE"):
        from app.services.screenshot_ingestion import screenshot_ingestion_service
        res = screenshot_ingestion_service.ingest_screenshot(contents, filename=file.filename)
        extracted_text = res.extracted_text
        inp_type = InputType.SCREENSHOT
    elif norm_type in ("VOICE", "AUDIO"):
        from app.services.voice_ingestion import voice_ingestion_service
        res = voice_ingestion_service.ingest_voice(contents, filename=file.filename)
        extracted_text = res.transcript
        inp_type = InputType.VOICE
    elif norm_type == "PDF":
        from app.services.pdf_ingestion import pdf_ingestion_service
        res = pdf_ingestion_service.ingest_pdf(contents, filename=file.filename)
        extracted_text = res.extracted_text
        inp_type = InputType.PDF
    else:
        extracted_text = contents.decode("utf-8", errors="ignore")
        inp_type = InputType.TEXT

    if not extracted_text.strip():
        extracted_text = f"[Attached {norm_type} file: {file.filename}]"

    job = job_manager.create_check_job(
        text=extracted_text,
        input_type=inp_type,
        background_tasks=background_tasks,
    )
    return CheckCreateResponse(
        check_id=job.check_id,
        status="RECEIVED",
    )


@router.get(
    "",
    response_model=List[CheckDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="List recent verification checks",
    description="Returns real checks stored in repository ordered newest first.",
)
async def list_checks(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
) -> List[CheckDetailResponse]:
    checks = job_manager.list_checks(limit=limit, status=status)
    results: List[CheckDetailResponse] = []
    for check in checks:
        claims = check.result.claims if (check.result and check.result.claims) else []
        results.append(
            CheckDetailResponse(
                check_id=check.check_id,
                status=check.status.value,
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


@router.get(
    "/stats/summary",
    status_code=status.HTTP_200_OK,
    summary="Aggregated analytics summary computed from genuine stored checks",
)
async def get_checks_stats() -> Dict[str, Any]:
    return job_manager.get_stats()


@router.get(
    "/{check_id}",
    response_model=CheckDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve complete verification check overview",
    description="Returns full verification check details, status, timestamps, and findings if finished.",
)
async def get_check(check_id: str) -> CheckDetailResponse:
    """
    GET /api/v1/checks/{check_id}
    """
    check = job_manager.get_check(check_id)
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Check '{check_id}' not found.",
        )

    claims = check.result.claims if (check.result and check.result.claims) else []
    return CheckDetailResponse(
        check_id=check.check_id,
        status=check.status.value,
        input_type=check.input.input_type.value if hasattr(check.input.input_type, "value") else str(check.input.input_type),
        text=check.input.raw_content,
        created_at=check.created_at,
        updated_at=check.updated_at,
        completed_at=check.result.completed_at if check.result else None,
        claims=claims,
        result=check.result,
    )


@router.get(
    "/{check_id}/status",
    response_model=CheckStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Poll verification check progress and state",
    description="Returns current execution status and active stage for a submitted check.",
)
async def get_check_status(check_id: str) -> CheckStatusResponse:
    """
    GET /api/v1/checks/{check_id}/status
    """
    st = job_manager.get_status(check_id)
    if not st:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Check '{check_id}' not found.",
        )
    return CheckStatusResponse(**st)


@router.get(
    "/{check_id}/claims",
    response_model=CheckClaimsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve extracted atomic claims for check",
    description="Returns verified atomic claims and individual rule verdicts for the check.",
)
async def get_check_claims(check_id: str) -> CheckClaimsResponse:
    """
    GET /api/v1/checks/{check_id}/claims
    """
    claims = job_manager.get_claims(check_id)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Check '{check_id}' not found.",
        )
    return CheckClaimsResponse(
        check_id=check_id,
        claims=claims,
    )


@router.get(
    "/{check_id}/evidence",
    response_model=CheckEvidenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve validated grounding evidence items",
    description="Returns verbatim locked citations and authoritative sources corroborating or refuting claims.",
)
async def get_check_evidence(check_id: str) -> CheckEvidenceResponse:
    """
    GET /api/v1/checks/{check_id}/evidence
    """
    evidence = job_manager.get_evidence(check_id)
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Check '{check_id}' not found.",
        )
    return CheckEvidenceResponse(
        check_id=check_id,
        evidence=evidence,
    )


@router.get(
    "/{check_id}/result",
    status_code=status.HTTP_200_OK,
    summary="Retrieve final VerificationResult",
    description="Returns final VerificationResult dossier if completed, or 202 Accepted if still processing.",
)
async def get_check_result(check_id: str):
    """
    GET /api/v1/checks/{check_id}/result
    """
    check = job_manager.get_check(check_id)
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Check '{check_id}' not found.",
        )

    if check.result:
        return check.result

    # If still processing, return HTTP 202 Accepted with status message
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "check_id": check_id,
            "status": check.status.value,
            "message": "Verification is in progress. Please poll status or check back shortly.",
        },
    )

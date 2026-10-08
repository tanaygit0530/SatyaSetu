import time
from typing import Any, Dict
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status

from app.core.exceptions import InvalidInputException
from app.core.logging import logger
from app.core.security.phone_hasher import phone_hasher
from app.services.whatsapp import whatsapp_webhook_service

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Twilio Integration"])


@router.post(
    "/webhook",
    summary="Twilio WhatsApp Webhook",
    description=(
        "Receives incoming WhatsApp citizen submissions (text, image, audio, PDF, media) from Twilio. "
        "Validates signature, deduplicates MessageSid, immediately acknowledges in non-blocking TwiML, "
        "and executes verification asynchronously via VerificationOrchestrator and Twilio REST API."
    ),
    response_class=Response,
)
async def twilio_whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Response:
    """
    POST /api/v1/whatsapp/webhook
    Pipeline:
    Twilio -> Webhook -> Structured log -> Validate Twilio signature ->
    Deduplicate MessageSid -> Parse WhatsAppIncomingMessage ->
    Immediate Acknowledgment TwiML -> Background Worker (VerificationOrchestrator) ->
    Twilio Outbound REST API -> WhatsApp Citizen Response
    """
    t_start = time.time()

    # 1. Parse form parameters sent by Twilio (application/x-www-form-urlencoded)
    try:
        form_data = await request.form()
        params = {k: v for k, v in form_data.items() if isinstance(v, str)}
    except Exception as e:
        logger.error("Failed to parse form data in WhatsApp webhook: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed form data payload.",
        )

    # 2. Extract fields for Step 2 structured logging (never log raw phone numbers or secrets)
    message_sid = params.get("MessageSid") or params.get("SmsMessageSid") or "unknown"
    account_sid = params.get("AccountSid") or "unknown"
    raw_from = params.get("From") or ""
    raw_to = params.get("To") or ""
    body_text = params.get("Body") or ""
    num_media = params.get("NumMedia") or "0"

    hashed_from = phone_hasher.hash_phone(raw_from) if raw_from else "unknown"

    logger.info(
        "WhatsApp Webhook REQUEST RECEIVED: MessageSid=%s | AccountSid=%s | From=%s | To=%s | BodyLen=%d | NumMedia=%s",
        message_sid,
        account_sid,
        hashed_from,
        raw_to,
        len(body_text),
        num_media,
    )

    # 3. Extract Twilio signature header and request URL
    signature = request.headers.get("X-Twilio-Signature")

    # Use forwarded headers if behind reverse proxy / ngrok
    proto = request.headers.get("X-Forwarded-Proto")
    host = request.headers.get("X-Forwarded-Host")
    if proto and host:
        request_url = f"{proto}://{host}{request.url.path}"
        if request.url.query:
            request_url += f"?{request.url.query}"
    else:
        request_url = str(request.url)

    logger.debug("WhatsApp Webhook processing start: MessageSid=%s | URL=%s", message_sid, request_url)

    # 4. Process through WhatsApp webhook service pipeline
    try:
        twiml_response = await whatsapp_webhook_service.process_webhook(
            form_data=params,
            request_url=request_url,
            signature=signature,
            background_tasks=background_tasks,
        )
        elapsed_ms = int((time.time() - t_start) * 1000)
        logger.info(
            "WhatsApp Webhook PROCESSING END: MessageSid=%s | HTTP 200 OK | Duration=%dms",
            message_sid,
            elapsed_ms,
        )
        return Response(
            content=twiml_response,
            media_type="application/xml",
            status_code=status.HTTP_200_OK,
        )

    except InvalidInputException as e:
        elapsed_ms = int((time.time() - t_start) * 1000)
        if "signature" in str(e).lower():
            logger.warning(
                "WhatsApp Webhook signature validation REJECTED: MessageSid=%s | HTTP 403 Forbidden | Duration=%dms | %s",
                message_sid,
                elapsed_ms,
                e,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        logger.warning("WhatsApp input error: MessageSid=%s | %s", message_sid, e)
        friendly_twiml = whatsapp_webhook_service.build_twiml_response(
            f"⚠️ Could not process message: {str(e)}"
        )
        return Response(
            content=friendly_twiml,
            media_type="application/xml",
            status_code=status.HTTP_200_OK,
        )

    except Exception as e:
        elapsed_ms = int((time.time() - t_start) * 1000)
        logger.error(
            "WhatsApp Webhook unexpected error: MessageSid=%s | HTTP 200 Fallback | Duration=%dms | %s",
            message_sid,
            elapsed_ms,
            e,
            exc_info=True,
        )
        fallback_twiml = whatsapp_webhook_service.build_twiml_response(
            "⚠️ An unexpected error occurred while verifying your request. Please try again later."
        )
        return Response(
            content=fallback_twiml,
            media_type="application/xml",
            status_code=status.HTTP_200_OK,
        )

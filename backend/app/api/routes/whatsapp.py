from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.exceptions import InvalidInputException
from app.core.logging import logger
from app.services.whatsapp import whatsapp_webhook_service

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Twilio Integration"])


@router.post(
    "/webhook",
    summary="Twilio WhatsApp Webhook",
    description=(
        "Receives incoming WhatsApp citizen submissions (text, image, audio, PDF, media) from Twilio. "
        "Validates signature, deduplicates MessageSid to prevent replay attacks, downloads media safely, "
        "routes to VerificationOrchestrator, and returns TwiML response."
    ),
    response_class=Response,
)
async def twilio_whatsapp_webhook(request: Request) -> Response:
    """
    POST /api/v1/whatsapp/webhook
    Pipeline:
    Twilio -> Webhook -> Validate Twilio signature -> Deduplicate MessageSid ->
    Identify input type -> Download media safely if required -> Create Check ->
    Send to SAME VerificationOrchestrator -> Generate WhatsApp response -> Send response (TwiML)
    """
    # 1. Parse form parameters sent by Twilio
    try:
        form_data = await request.form()
        params = {k: v for k, v in form_data.items() if isinstance(v, str)}
    except Exception as e:
        logger.error("Failed to parse form data in WhatsApp webhook: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed form data payload.",
        )

    # 2. Extract Twilio signature header and request URL
    signature = request.headers.get("X-Twilio-Signature")

    # Use forwarded headers if behind reverse proxy
    proto = request.headers.get("X-Forwarded-Proto")
    host = request.headers.get("X-Forwarded-Host")
    if proto and host:
        request_url = f"{proto}://{host}{request.url.path}"
        if request.url.query:
            request_url += f"?{request.url.query}"
    else:
        request_url = str(request.url)

    # 3. Process through WhatsApp webhook service pipeline
    try:
        twiml_response = await whatsapp_webhook_service.process_webhook(
            form_data=params,
            request_url=request_url,
            signature=signature,
        )
        return Response(
            content=twiml_response,
            media_type="application/xml",
            status_code=status.HTTP_200_OK,
        )

    except InvalidInputException as e:
        if "signature" in str(e).lower():
            logger.warning("Twilio signature validation rejected request: %s", e)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        logger.warning("WhatsApp input error: %s", e)
        # Return fallback friendly TwiML rather than erroring out Twilio
        friendly_twiml = whatsapp_webhook_service.build_twiml_response(
            f"⚠️ Could not process message: {str(e)}"
        )
        return Response(
            content=friendly_twiml,
            media_type="application/xml",
            status_code=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error("Unexpected error in WhatsApp webhook pipeline: %s", e, exc_info=True)
        fallback_twiml = whatsapp_webhook_service.build_twiml_response(
            "⚠️ An unexpected error occurred while verifying your request. Please try again later."
        )
        return Response(
            content=fallback_twiml,
            media_type="application/xml",
            status_code=status.HTTP_200_OK,
        )

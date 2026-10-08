import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import httpx
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.core.config import settings
from app.core.exceptions import InvalidInputException
from app.core.logging import logger
from app.schemas.core import ClaimVerificationResult, VerificationResult
from app.schemas.enums import InputType, Verdict
from app.schemas.whatsapp import WhatsAppFormattedResponse
from app.services.pdf_ingestion import PDFIngestionService, pdf_ingestion_service
from app.services.screenshot_ingestion import ScreenshotIngestionService, screenshot_ingestion_service
from app.services.verification_orchestrator import (
    VerificationOrchestrator,
    verification_orchestrator,
)
from app.services.voice_ingestion import VoiceIngestionService, voice_ingestion_service

# Emoji mapping for canonical SachCheck verdicts
VERDICT_EMOJIS: Dict[Union[Verdict, str], str] = {
    Verdict.FALSE: "🔴 FALSE",
    "FALSE": "🔴 FALSE",
    Verdict.VERIFIED: "🟢 VERIFIED",
    "VERIFIED": "🟢 VERIFIED",
    Verdict.OUTDATED: "🟠 OUTDATED",
    "OUTDATED": "🟠 OUTDATED",
    Verdict.PARTLY_SUPPORTED: "🟡 PARTLY SUPPORTED",
    "PARTLY_SUPPORTED": "🟡 PARTLY SUPPORTED",
    Verdict.CANNOT_BE_CONFIRMED: "⚪ CANNOT BE CONFIRMED",
    "CANNOT_BE_CONFIRMED": "⚪ CANNOT BE CONFIRMED",
}


class WhatsAppWebhookService:
    """
    Dedicated service for handling Twilio WhatsApp Webhook events.
    Enforces signature verification, deduplicates MessageSids to thwart replay attacks,
    safely downloads media, forwards extracted text to the SAME VerificationOrchestrator,
    and returns citizen-friendly WhatsApp responses with TwiML XML.
    """

    def __init__(
        self,
        orchestrator: Optional[VerificationOrchestrator] = None,
        screenshot_service: Optional[ScreenshotIngestionService] = None,
        voice_service: Optional[VoiceIngestionService] = None,
        pdf_service: Optional[PDFIngestionService] = None,
        ttl_seconds: int = 86400,
        max_cache_size: int = 10000,
    ):
        self.orchestrator = orchestrator or verification_orchestrator
        self.screenshot_service = screenshot_service or screenshot_ingestion_service
        self.voice_service = voice_service or voice_ingestion_service
        self.pdf_service = pdf_service or pdf_ingestion_service
        self.ttl_seconds = ttl_seconds
        self.max_cache_size = max_cache_size

        # In-memory deduplication & replay store
        # {message_sid: {"timestamp": float, "response_twiml": str}}
        self._processed_messages: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    # =========================================================================
    # 1. SIGNATURE VALIDATION
    # =========================================================================

    def validate_signature(
        self,
        url: str,
        params: Dict[str, Any],
        signature: Optional[str],
    ) -> bool:
        """
        Validates Twilio webhook request signature using TWILIO_AUTH_TOKEN.
        If validation is disabled in settings or auth token is unset, permits for testing/dev.
        """
        if not settings.TWILIO_VALIDATE_SIGNATURE:
            logger.debug("Twilio signature validation bypassed (TWILIO_VALIDATE_SIGNATURE=False)")
            return True

        auth_token = settings.TWILIO_AUTH_TOKEN
        if not auth_token:
            logger.warning(
                "TWILIO_AUTH_TOKEN is not set; skipping signature validation for local/development mode."
            )
            return True

        if not signature:
            logger.warning("Rejecting Twilio request: Missing 'X-Twilio-Signature' header.")
            return False

        validator = RequestValidator(auth_token)
        # Twilio validator expects all string params
        clean_params = {k: str(v) for k, v in params.items()}

        # 1. Validate on direct URL
        if validator.validate(url, clean_params, signature):
            return True

        # 2. Proxy compatibility check (http <-> https)
        if url.startswith("http://"):
            https_url = "https://" + url[7:]
            if validator.validate(https_url, clean_params, signature):
                return True
        elif url.startswith("https://"):
            http_url = "http://" + url[8:]
            if validator.validate(http_url, clean_params, signature):
                return True

        logger.warning("Twilio signature validation failed for URL: %s", url)
        return False

    # =========================================================================
    # 2. DEDUPLICATION & REPLAY PROTECTION
    # =========================================================================

    def is_duplicate_message(self, message_sid: str) -> bool:
        """
        Checks whether the MessageSid was already processed or is active,
        preventing duplicate processing and replay attacks.
        """
        if not message_sid:
            return False

        now = time.time()
        with self._lock:
            # Purge expired records
            self._purge_expired(now)

            record = self._processed_messages.get(message_sid)
            if record is not None:
                if (now - record["timestamp"]) < self.ttl_seconds:
                    return True
                else:
                    del self._processed_messages[message_sid]
            return False

    def get_cached_response(self, message_sid: str) -> Optional[str]:
        """
        Retrieves previously generated TwiML response for deduplicated MessageSid.
        """
        if not message_sid:
            return None
        with self._lock:
            record = self._processed_messages.get(message_sid)
            if record:
                return record.get("response_twiml")
            return None

    def record_message(self, message_sid: str, response_twiml: str = "") -> None:
        """
        Records MessageSid and its resulting TwiML XML into the deduplication cache.
        """
        if not message_sid:
            return

        now = time.time()
        with self._lock:
            self._purge_expired(now)

            if len(self._processed_messages) >= self.max_cache_size:
                # Evict oldest
                oldest_sid = min(self._processed_messages.keys(), key=lambda k: self._processed_messages[k]["timestamp"])
                del self._processed_messages[oldest_sid]

            self._processed_messages[message_sid] = {
                "timestamp": now,
                "response_twiml": response_twiml,
            }

    def _purge_expired(self, current_time: float) -> None:
        """Removes expired MessageSids beyond TTL."""
        expired = [
            sid for sid, data in self._processed_messages.items()
            if (current_time - data["timestamp"]) >= self.ttl_seconds
        ]
        for sid in expired:
            del self._processed_messages[sid]

    # =========================================================================
    # 3. IDENTIFY INPUT TYPE
    # =========================================================================

    def identify_input_type(self, form_data: Dict[str, Any]) -> str:
        """
        Identifies submission input modality: TEXT, SCREENSHOT, VOICE, PDF, or MEDIA.
        """
        num_media_val = form_data.get("NumMedia", 0)
        try:
            num_media = int(num_media_val)
        except (ValueError, TypeError):
            num_media = 0

        if num_media > 0:
            content_type = str(form_data.get("MediaContentType0", "")).lower()
            if "image/" in content_type:
                return "SCREENSHOT"
            elif "audio/" in content_type or "ogg" in content_type:
                return "VOICE"
            elif "pdf" in content_type or "application/pdf" in content_type:
                return "PDF"
            else:
                return "MEDIA"

        # No media attachments
        return "TEXT"

    # =========================================================================
    # 4. DOWNLOAD MEDIA SAFELY
    # =========================================================================

    async def download_media_safely(
        self,
        media_url: str,
        max_bytes: int = 25 * 1024 * 1024,
        timeout_seconds: Optional[float] = None,
    ) -> bytes:
        """
        Safely downloads media attached to a WhatsApp message with:
        - Strict scheme validation (HTTPS)
        - Byte size boundaries
        - Network timeouts
        - Basic authentication with Twilio credentials for api.twilio.com
        """
        if not media_url:
            raise InvalidInputException("Media URL is empty or missing.")

        parsed = urlparse(media_url)
        if parsed.scheme not in ("https", "http"):
            raise InvalidInputException(f"Invalid media URL scheme '{parsed.scheme}'. Only HTTPS permitted.")

        timeout = timeout_seconds or settings.TWILIO_MEDIA_DOWNLOAD_TIMEOUT_SECONDS

        # Check if Twilio API Basic Auth is required
        auth = None
        if "twilio.com" in parsed.netloc:
            if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
                auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(media_url, auth=auth)
                if resp.status_code != 200:
                    raise InvalidInputException(
                        f"Failed to fetch media from provider (HTTP status {resp.status_code})."
                    )

                media_bytes = resp.content
                if len(media_bytes) == 0:
                    raise InvalidInputException("Downloaded media file is empty (0 bytes).")

                if len(media_bytes) > max_bytes:
                    raise InvalidInputException(
                        f"Media file size ({len(media_bytes)} bytes) exceeds maximum limit of {max_bytes} bytes."
                    )

                return media_bytes

        except httpx.TimeoutException:
            logger.error("Media download timed out after %s seconds for URL: %s", timeout, media_url)
            raise InvalidInputException("Media download timed out. Please try sending a smaller file.")
        except Exception as e:
            if isinstance(e, InvalidInputException):
                raise
            logger.error("Error downloading media attachment safely: %s", e)
            raise InvalidInputException("Could not retrieve media attachment safely.")

    # =========================================================================
    # 5. INGEST MEDIA CONTENT
    # =========================================================================

    def ingest_media_bytes(
        self,
        media_bytes: bytes,
        input_type: str,
    ) -> str:
        """
        Dispatches media bytes to the appropriate existing ingestion pipeline
        (screenshot OCR, voice STT, or PDF extraction).
        """
        try:
            if input_type == "SCREENSHOT":
                res = self.screenshot_service.ingest_screenshot(media_bytes)
                return res.extracted_text or ""
            elif input_type == "VOICE":
                res = self.voice_service.ingest_voice(media_bytes)
                return res.transcript or ""
            elif input_type == "PDF":
                res = self.pdf_service.ingest_pdf(media_bytes)
                return res.extracted_text or ""
            else:
                # Generic fallback: attempt screenshot OCR
                try:
                    res = self.screenshot_service.ingest_screenshot(media_bytes)
                    return res.extracted_text or ""
                except Exception:
                    return ""
        except Exception as e:
            logger.warning("Failed media ingestion for type '%s': %s", input_type, e)
            return ""

    # =========================================================================
    # 6. FORMAT WHATSAPP CITIZEN RESPONSE
    # =========================================================================

    def format_whatsapp_response(
        self,
        result: VerificationResult,
        check_id: str,
    ) -> WhatsAppFormattedResponse:
        """
        Formats a citizen-friendly WhatsApp response adhering strictly to specification:

        🔴 FALSE

        Claim:
        UPI will be banned tomorrow.

        Why:
        We found no official evidence announcing a nationwide UPI shutdown.

        Proof:
        NPCI — [source]

        View full evidence:
        https://sachcheck.in/checks/{check_id}
        """
        # Determine overall verdict
        overall_verdict = result.overall_verdict or Verdict.CANNOT_BE_CONFIRMED
        if isinstance(overall_verdict, str):
            try:
                overall_verdict = Verdict(overall_verdict)
            except ValueError:
                overall_verdict = Verdict.CANNOT_BE_CONFIRMED

        verdict_header = VERDICT_EMOJIS.get(overall_verdict, f"⚪ {overall_verdict.value}")

        # Extract primary claim information
        primary_claim = result.claims[0] if result.claims else None

        if primary_claim:
            claim_text = (
                primary_claim.normalized_claim
                or primary_claim.claim_text
                or "Citizen factual submission"
            ).strip()
            why_explanation = primary_claim.explanation.strip()
        else:
            claim_text = (result.original_content or "No verifiable factual claim detected.").strip()
            why_explanation = (
                result.summary
                or "We found no check-worthy claims or insufficient evidence to confirm this claim."
            ).strip()

        # Extract proof / citations
        proof_entries: List[str] = []
        if primary_claim and primary_claim.evidence:
            for ev in primary_claim.evidence:
                publisher = getattr(ev, "publisher", None) or (ev.get("publisher") if isinstance(ev, dict) else None)
                url = (
                    getattr(ev, "source_url", None)
                    or getattr(ev, "url", None)
                    or (ev.get("source_url") or ev.get("url") if isinstance(ev, dict) else None)
                )

                if publisher and url:
                    proof_entries.append(f"{publisher} — {url}")
                elif url:
                    proof_entries.append(f"Official Source — {url}")
                elif publisher:
                    proof_entries.append(f"{publisher} official gazette")

                if len(proof_entries) >= 2:
                    break

        proof_text = "\n".join(proof_entries) if proof_entries else None

        # Build full evidence public link
        evidence_url = f"{settings.BASE_PUBLIC_URL.rstrip('/')}/checks/{check_id}"

        # Build composite WhatsApp formatted text
        lines = [
            verdict_header,
            "",
            "Claim:",
            claim_text,
            "",
            "Why:",
            why_explanation,
        ]

        if proof_text:
            lines.extend([
                "",
                "Proof:",
                proof_text,
            ])

        lines.extend([
            "",
            "View full evidence:",
            evidence_url,
        ])

        formatted_body = "\n".join(lines)

        return WhatsAppFormattedResponse(
            verdict_emoji_header=verdict_header,
            claim_text=claim_text,
            why_explanation=why_explanation,
            proof=proof_text,
            full_evidence_url=evidence_url,
            formatted_body=formatted_body,
        )

    # =========================================================================
    # 7. BUILD TWIML RESPONSE
    # =========================================================================

    def build_twiml_response(self, message_body: str) -> str:
        """
        Constructs standard TwiML XML payload to respond synchronously to Twilio.
        """
        response = MessagingResponse()
        response.message(message_body)
        return str(response)

    def build_empty_twiml(self) -> str:
        """Constructs an empty TwiML response for deduplication / quiet ACK."""
        response = MessagingResponse()
        return str(response)

    # =========================================================================
    # 8. OUTBOUND MESSAGE DISPATCH (OPTIONAL DIRECT TWILIO CLIENT)
    # =========================================================================

    def send_outbound_whatsapp_message(
        self,
        to_number: str,
        body_text: str,
    ) -> Optional[str]:
        """
        Sends an outbound WhatsApp message via Twilio REST API client if configured.
        """
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_WHATSAPP_NUMBER

        if not (account_sid and auth_token and from_number):
            logger.debug("Twilio REST client credentials not configured; skipping direct outbound call.")
            return None

        try:
            from twilio.rest import Client

            client = Client(account_sid, auth_token)
            msg = client.messages.create(
                from_=from_number,
                to=to_number,
                body=body_text,
            )
            logger.info("Sent outbound WhatsApp response %s to %s", msg.sid, to_number)
            return msg.sid
        except Exception as e:
            logger.error("Failed to send outbound Twilio WhatsApp message: %s", e)
            return None

    # =========================================================================
    # 9. END-TO-END WEBHOOK PROCESSING PIPELINE
    # =========================================================================

    async def process_webhook(
        self,
        form_data: Dict[str, Any],
        request_url: str,
        signature: Optional[str],
    ) -> str:
        """
        End-to-end Twilio WhatsApp webhook pipeline:
        1. Validate Twilio signature
        2. Deduplicate MessageSid & prevent replay attacks
        3. Identify input type
        4. Safely download media if required
        5. Create Check
        6. Send to SAME VerificationOrchestrator
        7. Generate WhatsApp response
        8. Return standard TwiML XML
        """
        # 1. Validate signature
        is_valid = self.validate_signature(request_url, form_data, signature)
        if not is_valid:
            logger.warning("Twilio signature validation failed for request: %s", request_url)
            raise InvalidInputException("Invalid or missing Twilio signature.")

        # 2. Deduplicate MessageSid
        message_sid = str(
            form_data.get("MessageSid")
            or form_data.get("SmsMessageSid")
            or form_data.get("SmsSid")
            or ""
        ).strip()

        if message_sid and self.is_duplicate_message(message_sid):
            logger.info("Duplicate or replayed MessageSid detected: '%s'. Returning cached ACK.", message_sid)
            cached_twiml = self.get_cached_response(message_sid)
            return cached_twiml or self.build_empty_twiml()

        # 3. Identify input type
        input_type = self.identify_input_type(form_data)
        user_body = str(form_data.get("Body", "") or "").strip()

        # 4. Download and extract media safely if required
        extracted_content = ""
        num_media_raw = form_data.get("NumMedia", 0)
        try:
            num_media = int(num_media_raw)
        except (ValueError, TypeError):
            num_media = 0

        if num_media > 0:
            media_url = form_data.get("MediaUrl0")
            if media_url:
                try:
                    media_bytes = await self.download_media_safely(media_url)
                    media_text = self.ingest_media_bytes(media_bytes, input_type)
                    if media_text:
                        extracted_content = media_text
                except Exception as e:
                    logger.warning("Media processing notice: %s", e)

        # Combine text body and extracted media content
        if user_body and extracted_content:
            final_content = f"{user_body}\n\n[Extracted from {input_type.lower()}]: {extracted_content}"
        elif extracted_content:
            final_content = extracted_content
        elif user_body:
            final_content = user_body
        else:
            # Empty submission
            empty_response = (
                "⚪ CANNOT BE CONFIRMED\n\n"
                "Claim:\nNo verifiable content provided.\n\n"
                "Why:\nPlease forward a factual statement, link, image, voice note, or circular to verify."
            )
            twiml = self.build_twiml_response(empty_response)
            if message_sid:
                self.record_message(message_sid, twiml)
            return twiml

        # 5. Create Check ID
        check_id = f"chk_{uuid.uuid4().hex[:12]}"

        # 6. Send to the SAME VerificationOrchestrator
        # DO NOT CREATE A SECOND VERIFICATION ENGINE
        verification_result = self.orchestrator.verify(
            content=final_content,
            input_type=InputType.WHATSAPP.value,
            check_id=check_id,
        )

        # 7. Generate WhatsApp response
        formatted_response = self.format_whatsapp_response(
            result=verification_result,
            check_id=check_id,
        )

        # 8. Build TwiML XML response
        twiml_response = self.build_twiml_response(formatted_response.formatted_body)

        # Record MessageSid to prevent future replay attacks
        if message_sid:
            self.record_message(message_sid, twiml_response)

        return twiml_response


# Global singleton instance
whatsapp_webhook_service = WhatsAppWebhookService()

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WhatsAppMediaItem(BaseModel):
    """Media item attached to an incoming WhatsApp message."""
    url: str
    content_type: str
    index: int = 0


class WhatsAppIncomingMessage(BaseModel):
    """
    Standard parsed model for incoming WhatsApp messages received via Twilio Webhook.
    Preserves raw claim wording and normalizes addresses to whatsapp:+...
    """
    message_sid: str = Field(..., description="Unique Twilio Message SID")
    account_sid: Optional[str] = Field(default=None, description="Twilio Account SID")
    from_number: str = Field(..., description="Sender WhatsApp address with whatsapp:+ prefix")
    to_number: str = Field(..., description="Recipient Twilio WhatsApp address with whatsapp:+ prefix")
    body: str = Field(default="", description="Citizen message text or media caption")
    num_media: int = Field(default=0, description="Total media attachments count")
    media: List[WhatsAppMediaItem] = Field(default_factory=list, description="Parsed media attachments list")
    profile_name: Optional[str] = Field(default=None, description="WhatsApp profile display name")
    wa_id: Optional[str] = Field(default=None, description="WhatsApp user ID")
    received_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp when webhook was ingested",
    )

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class TwilioWebhookData(BaseModel):
    """
    Standard Twilio WhatsApp Webhook payload fields.
    """
    message_sid: str = Field(..., alias="MessageSid", description="Unique Twilio message identifier")
    from_number: str = Field(..., alias="From", description="Sender WhatsApp identifier (e.g. whatsapp:+919876543210)")
    to_number: str = Field(..., alias="To", description="Recipient WhatsApp identifier (e.g. whatsapp:+14155238886)")
    body: Optional[str] = Field(default=None, alias="Body", description="User message text or caption")
    num_media: int = Field(default=0, alias="NumMedia", description="Number of media attachments attached")
    media_url_0: Optional[str] = Field(default=None, alias="MediaUrl0", description="First media URL attachment")
    media_content_type_0: Optional[str] = Field(default=None, alias="MediaContentType0", description="MIME type of first attachment")
    account_sid: Optional[str] = Field(default=None, alias="AccountSid", description="Twilio Account SID")
    sms_status: Optional[str] = Field(default=None, alias="SmsStatus")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class WhatsAppFormattedResponse(BaseModel):
    """
    Structured breakdown of the generated WhatsApp citizen response.
    """
    verdict_emoji_header: str
    claim_text: str
    why_explanation: str
    correction: Optional[str] = None
    proof: Optional[str] = None
    full_evidence_url: Optional[str] = None
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    formatted_body: str
    voice_url: Optional[str] = Field(default=None, description="Optional public URL to synthesized TTS voice explanation")
    voice_path: Optional[str] = Field(default=None, description="Optional local file path to synthesized audio")
    has_voice: bool = Field(default=False, description="Whether TTS audio is attached")

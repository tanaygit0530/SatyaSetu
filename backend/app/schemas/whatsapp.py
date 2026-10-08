from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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

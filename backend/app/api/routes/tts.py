import os
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.tts import tts_service

router = APIRouter(prefix="/tts", tags=["Text-to-Speech (TTS)"])


class TTSSynthesizeRequest(BaseModel):
    explanation: str = Field(..., min_length=2, description="Final explanation text to synthesize into speech")
    language: str = Field(default="en", description="Target language: en, hi, or mr")


class TTSSynthesizeResponse(BaseModel):
    success: bool = Field(..., description="Whether voice synthesis succeeded")
    audio_path: Optional[str] = Field(None, description="Local path to synthesized audio file")
    audio_url: Optional[str] = Field(None, description="Public streaming URL for audio")
    format: str = Field(default="mp3")
    language: str = Field(default="en")
    provider: str = Field(default="sarvam")
    latency_ms: float = Field(default=0.0)
    error: Optional[str] = None


@router.post(
    "/synthesize",
    response_model=TTSSynthesizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Synthesize final explanation text into speech audio",
    description="Uses Sarvam TTS if configured. If TTS fails, returns success=False and does not block the caller.",
)
async def synthesize_speech_endpoint(payload: TTSSynthesizeRequest) -> TTSSynthesizeResponse:
    """Synthesizes explanation into speech audio file in English, Hindi, or Marathi."""
    result = tts_service.synthesize_explanation(
        explanation=payload.explanation,
        language=payload.language,
    )
    return TTSSynthesizeResponse(
        success=result.success,
        audio_path=result.audio_path,
        audio_url=result.audio_url,
        format=result.format,
        language=result.language,
        provider=result.provider,
        latency_ms=result.latency_ms,
        error=result.error,
    )


@router.get(
    "/audio/{filename}",
    summary="Serve generated audio file",
)
async def get_audio_file_endpoint(filename: str):
    """Streams the synthesized MP3 audio file."""
    audio_dir = getattr(settings, "TTS_AUDIO_DIR", "/tmp/sachcheck_audio")
    file_path = os.path.join(audio_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)

"""TTS API router for Kokoro Japanese Voice synthesis and Low-VRAM guardrails."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel, Field

from app.services.tts_service import (
    KOKORO_JAPANESE_VOICES,
    TACHYON_LIKE_VOICE,
    TTSService,
    VRAMGuardrail,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])

# Shared singleton service instance
_tts_service = TTSService()


def get_tts_service() -> TTSService:
    """Return the active TTSService instance."""
    return _tts_service


# ---------------------------------------------------------------------------
# Request and Response Models
# ---------------------------------------------------------------------------

class TTSGenerateRequest(BaseModel):
    """Request payload for Dr. Agnes Tachyon Japanese voice synthesis."""

    text: str = Field(..., description="Dialogue or commentary text (English or Japanese).")
    mood: str = Field(
        default="thinking",
        description="Character mood: 'flow', 'happy', 'thinking', 'shocked', 'serious', 'tired'.",
    )
    language: str = Field(default="ja", description="Target speech language ('ja' for Japanese).")
    voice: str = Field(default="jf_nezumi", description="Kokoro voice pack (e.g. 'jf_nezumi', 'jf_alpha').")
    speed: float | None = Field(default=None, description="Optional speed multiplier.")
    stream: bool = Field(default=False, description="Whether to stream raw audio bytes directly.")
    fallback_synthetic: bool = Field(
        default=True,
        description="Whether to generate lightweight pure-Python CPU audio if cloud API key is absent.",
    )


class TTSGenerateResponse(BaseModel):
    """Structured response for dual-layer Japanese voice and English dialogue."""

    audio_base64: str | None = Field(None, description="Base64-encoded audio bytes.")
    audio_url: str | None = Field(None, description="Direct URL to audio asset if hosted.")
    media_type: str = Field(default="audio/mpeg", description="Audio MIME type.")
    subtitle_cue: str = Field(..., description="Localized Japanese subtitle cue (e.g. 「ふふっ、我がモルモット君！」).")
    romanized_callout: str = Field(default="", description="Phonetic voice callout for English players.")
    english_text: str = Field(..., description="Original English enterprise architecture dialogue.")
    japanese_speech_text: str = Field(..., description="In-character Japanese speech text synthesized.")
    mood: str = Field(..., description="Normalized character mood.")
    voice: str = Field(..., description="Voice pack utilized.")
    speed: float = Field(..., description="Vocal speed factor.")
    device: str = Field(default="cpu", description="Enforced compute device (strictly 'cpu').")
    vram_allocated_mb: float = Field(default=0.0, description="VRAM tensor memory allocated in MB.")
    target_hardware: str = Field(
        default="AMD Radeon HD 5450 (2GB VRAM)",
        description="Attestation target hardware.",
    )


class TTSSynthesizeRequest(BaseModel):
    """Direct audio synthesis request payload."""

    text: str
    voice: str = "jf_nezumi"
    speed: float = 1.04
    mood: str = "thinking"
    fallback_synthetic: bool = True


# ---------------------------------------------------------------------------
# Router Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=TTSGenerateResponse)
async def generate_voice(
    req: TTSGenerateRequest,
    accept: str | None = Header(default=None),
) -> Any:
    """Generate dual-layer authentic Japanese voice audio & subtitle cues for Agnes Tachyon.

    Hardware Guardrail:
    - Runs strictly on CPU (or remote Featherless cloud API).
    - Guarantees 0 MB VRAM allocation on the host machine.
    """
    tts = get_tts_service()
    result = await tts.generate_voice(
        text=req.text,
        mood=req.mood,
        voice=req.voice,
        speed=req.speed,
        language=req.language,
        fallback_synthetic=req.fallback_synthetic,
    )

    audio_bytes = result.get("audio_bytes")

    # If stream requested or client explicitly asks for audio stream
    if req.stream or (accept and "audio" in accept.lower()):
        if not audio_bytes:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        import urllib.parse

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "X-Subtitle-Cue": urllib.parse.quote(result["subtitle_cue"]),
                "X-Romanized-Cue": result.get("romanized_callout", ""),
                "X-Device": result["device"],
                "X-Mood": result["mood"],
            },
        )

    return TTSGenerateResponse(
        audio_base64=result.get("audio_base64"),
        audio_url=None,
        media_type=result.get("media_type", "audio/mpeg"),
        subtitle_cue=result.get("subtitle_cue", ""),
        romanized_callout=result.get("romanized_callout", ""),
        english_text=result.get("english_text", req.text),
        japanese_speech_text=result.get("japanese_speech_text", ""),
        mood=result.get("mood", req.mood),
        voice=result.get("voice", req.voice),
        speed=result.get("speed", 1.04),
        device=result.get("device", "cpu"),
        vram_allocated_mb=result.get("vram_allocated_mb", 0.0),
        target_hardware=result.get("target_hardware", VRAMGuardrail.TARGET_HARDWARE),
    )


@router.post("/synthesize")
async def synthesize_speech(req: TTSSynthesizeRequest) -> Response:
    """Directly synthesize text into raw audio/mpeg bytes under CPU guardrails."""
    tts = get_tts_service()
    audio_bytes = await tts.synthesize(
        text=req.text,
        voice=req.voice,
        speed=req.speed,
        mood=req.mood,
        fallback_synthetic=req.fallback_synthetic,
    )
    if not audio_bytes:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    import urllib.parse

    cue_jp, cue_rom = tts.get_subtitle_cue(text=req.text, mood=req.mood)
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "X-Subtitle-Cue": urllib.parse.quote(cue_jp),
            "X-Romanized-Cue": cue_rom,
            "X-Device": "cpu",
        },
    )


@router.get("/guardrails")
async def get_guardrails() -> dict[str, Any]:
    """Inspect hardware and VRAM safety guardrails for the AMD Radeon HD 5450."""
    return VRAMGuardrail.verify_low_vram_safety()


@router.get("/voices")
async def get_voices() -> dict[str, Any]:
    """Retrieve available Kokoro Japanese voice packs and Tachyon acoustic blend."""
    return {
        "voices": [
            {"id": voice_id, **info}
            for voice_id, info in KOKORO_JAPANESE_VOICES.items()
        ],
        "default_voice": "jf_nezumi",
        "tachyon_mix": TACHYON_LIKE_VOICE,
    }


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return TTS service health and compute guardrail status."""
    return {
        "status": "ok",
        "service": "Kokoro-82M Japanese TTS",
        "device": "cpu",
        "guardrail": "AMD Radeon HD 5450 2GB VRAM Protection Active",
    }

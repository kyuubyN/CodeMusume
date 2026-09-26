"""Comprehensive unit tests for Kokoro Japanese Voice Backend & Low-VRAM Guardrails.

Validates:
- R3: Kokoro Japanese voice transformation (Agnes Tachyon persona, mood profiles, dual-layer subtitles)
- R4: Hardware & VRAM Guardrails for legacy AMD Radeon HD 5450 (2GB VRAM, CPU-only inference, 0MB VRAM)
- Pure-Python CPU audio generation
- TTSService client and error handling
- FastAPI TTS router endpoints (/api/tts/generate, /synthesize, /guardrails, /voices, /health)
"""
from __future__ import annotations

import base64
import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import Response as HttpxResponse

from app.main import app
from app.routers.tts import (
    TTSGenerateRequest,
    TTSGenerateResponse,
    TTSSynthesizeRequest,
    get_tts_service,
)
from app.services.tts_service import (
    KOKORO_JAPANESE_VOICES,
    MOOD_ACOUSTIC_PROFILES,
    TACHYON_LIKE_VOICE,
    TTSService,
    VRAMGuardrail,
    generate_minimal_audio_bytes,
)


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


# ===========================================================================
# 1. Low-VRAM Hardware Guardrail Tests (AMD Radeon HD 5450 - 2GB VRAM)
# ===========================================================================

class TestVRAMGuardrails:
    """Test suite ensuring strict CPU-only execution and zero GPU tensor allocation."""

    def test_cuda_visible_devices_env_masked(self) -> None:
        """Verify CUDA visibility is explicitly masked to protect 2GB host VRAM."""
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""

    @pytest.mark.parametrize(
        ("input_device", "expected_device"),
        [
            ("cuda", "cpu"),
            ("cuda:0", "cpu"),
            ("GPU", "cpu"),
            ("rocm", "cpu"),
            ("mps", "cpu"),
            (None, "cpu"),
            ("", "cpu"),
            ("cpu", "cpu"),
            ("CPU", "cpu"),
        ],
    )
    def test_device_sanitizer_strictly_coerces_to_cpu(
        self,
        input_device: str | None,
        expected_device: str,
    ) -> None:
        """Verify any attempt to request GPU/CUDA is coerced to 'cpu'."""
        assert VRAMGuardrail.sanitize_device(input_device) == expected_device

    def test_vram_usage_is_strictly_zero(self) -> None:
        """Verify local GPU VRAM allocation is 0.0 MB under CPU execution."""
        vram_mb = VRAMGuardrail.get_vram_usage_mb()
        assert vram_mb == 0.0

    def test_hardware_safety_attestation(self) -> None:
        """Verify comprehensive hardware safety status dictionary."""
        status = VRAMGuardrail.verify_low_vram_safety()
        assert status["device"] == "cpu"
        assert status["vram_limit_mb"] == 2048.0
        assert status["vram_allocated_mb"] == 0.0
        assert "AMD Radeon HD 5450" in status["target_hardware"]
        assert status["cuda_available"] is False
        assert status["guardrail_active"] is True
        assert "ACTIVE" in status["safety_attestation"]

    def test_tts_service_initializes_with_cpu_guardrail(self) -> None:
        """Verify TTSService forces device='cpu' even if cuda requested."""
        service = TTSService(device="cuda:0")
        assert service.get_device() == "cpu"
        guardrail = service.get_guardrail_status()
        assert guardrail["device"] == "cpu"
        assert guardrail["vram_allocated_mb"] == 0.0


# ===========================================================================
# 2. Kokoro Japanese Voices & Agnes Tachyon Acoustic Blend Tests
# ===========================================================================

class TestKokoroVoicesAndAcoustics:
    """Test suite validating Japanese voice packs, Agnes voice blend, and mood profiles."""

    def test_japanese_voice_catalog_contains_required_voices(self) -> None:
        """Verify Kokoro Japanese voices catalog contains jf_nezumi and jf_alpha."""
        assert "jf_nezumi" in KOKORO_JAPANESE_VOICES
        assert "jf_alpha" in KOKORO_JAPANESE_VOICES
        assert "jf_gongitsune" in KOKORO_JAPANESE_VOICES
        assert "jm_kumo" in KOKORO_JAPANESE_VOICES
        assert "jf_tekgok" in KOKORO_JAPANESE_VOICES

        # Check Tachyon primary voice suitability
        assert KOKORO_JAPANESE_VOICES["jf_nezumi"]["tachyon_suitability"] == "primary"
        assert KOKORO_JAPANESE_VOICES["jf_alpha"]["tachyon_suitability"] == "blend_secondary"

    def test_tachyon_signature_voice_mix(self) -> None:
        """Verify Agnes Tachyon's signature voice blend: 70% jf_nezumi + 30% jf_alpha."""
        assert TACHYON_LIKE_VOICE["voice"] == "jf_nezumi"
        mix = TACHYON_LIKE_VOICE["voice_mix"]
        assert mix["jf_nezumi"] == 0.70
        assert mix["jf_alpha"] == 0.30
        assert TACHYON_LIKE_VOICE["speed"] == 1.04
        assert TACHYON_LIKE_VOICE["pitch_semitones"] == -0.4

    @pytest.mark.parametrize(
        "mood",
        ["flow", "happy", "thinking", "shocked", "serious", "tired"],
    )
    def test_all_six_mood_profiles_configured(self, mood: str) -> None:
        """Verify acoustic profiles exist for all 6 character moods."""
        assert mood in MOOD_ACOUSTIC_PROFILES
        profile = MOOD_ACOUSTIC_PROFILES[mood]
        assert "speed" in profile
        assert "pitch_semitones" in profile
        assert "formant_shift" in profile
        assert "pause_scale" in profile
        assert "subtitle_cue" in profile
        assert "romanized_cue" in profile
        assert len(profile["subtitle_cue"]) > 0

    def test_available_voices_service_method(self) -> None:
        """Verify get_available_voices returns voice pack list with metadata."""
        service = TTSService()
        voices = service.get_available_voices()
        assert len(voices) >= 5
        voice_ids = [v["id"] for v in voices]
        assert "jf_nezumi" in voice_ids
        assert "jf_alpha" in voice_ids


# ===========================================================================
# 3. Japanese Dialogue Transformation & Subtitle Cue Tests
# ===========================================================================

class TestJapaneseTransformationAndSubtitles:
    """Test suite for dual-layer Japanese voice transformation and subtitle cues."""

    @pytest.mark.asyncio
    async def test_to_japanese_speech_preserves_existing_japanese(self) -> None:
        """Verify Japanese text is preserved when passed as input."""
        service = TTSService()
        original = "ククク… 我がモルモット君、実験は成功だ！"
        result = await service.to_japanese_speech(original)
        assert "モルモット" in result
        await service.close()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("english_phrase", "expected_keyword"),
        [
            ("Greetings, Morumotto-kun", "モルモット君"),
            ("grand software experiment", "ソフトウェア実験"),
            ("Rest is not laziness", "休息"),
            ("catastrophic metabolic failure", "モルモット君"),
            ("synthesized the cure", "光彩"),
            ("grand derby victory", "光彩"),
        ],
    )
    async def test_to_japanese_speech_canonical_lines(
        self,
        english_phrase: str,
        expected_keyword: str,
    ) -> None:
        """Verify canonical English game lines transform into in-character Japanese dialogue."""
        service = TTSService()
        result = await service.to_japanese_speech(english_phrase)
        assert expected_keyword in result
        assert "ククク" in result or "モルモット" in result or "アッハハ" in result or "ふぁぁ" in result or "何だって" in result
        await service.close()

    @pytest.mark.asyncio
    async def test_to_japanese_speech_offline_fallback(self) -> None:
        """Verify unknown dialogue in offline/test environment yields authentic Japanese line."""
        service = TTSService(api_key="")
        result = await service.to_japanese_speech("Arbitrary enterprise architecture query.")
        assert len(result) > 10
        # Verify result contains Japanese characters
        from app.services.tts_service import _has_japanese
        assert _has_japanese(result)
        await service.close()

    @pytest.mark.parametrize(
        ("mood", "expected_keywords"),
        [
            ("flow", ["光", "光彩", "限界", "アッハハ", "輝き"]),
            ("happy", ["モルモット", "素晴らしい", "喜ばしい", "データ"]),
            ("thinking", ["興味深い", "モルモット", "揺らぎ", "観察", "実験"]),
            ("shocked", ["何だって", "プランB", "特異点", "異常事態", "計算"]),
            ("serious", ["設計", "プロトコル", "真理", "実験", "曖昧"]),
            ("tired", ["紅茶", "角砂糖", "ソファ", "オーバーヒート"]),
        ],
    )
    def test_subtitle_cue_mood_mapping(
        self,
        mood: str,
        expected_keywords: list[str],
    ) -> None:
        """Verify localized Japanese subtitle cues match the given character mood."""
        service = TTSService()
        cue_jp, cue_rom = service.get_subtitle_cue(text="General line", mood=mood)
        assert any(k in cue_jp for k in expected_keywords), f"None of {expected_keywords} in {cue_jp}"
        assert len(cue_rom) > 0


# ===========================================================================
# 4. Pure-Python CPU Audio Generator Tests
# ===========================================================================

class TestSyntheticAudioGenerator:
    """Test suite for lightweight pure-Python audio generation (zero external dependencies)."""

    def test_generate_minimal_mp3_validity(self) -> None:
        """Verify MP3 generator produces valid MPEG-1 Layer 3 audio frames."""
        audio = generate_minimal_audio_bytes(duration_ms=500, format="mp3")
        assert isinstance(audio, bytes)
        assert len(audio) >= 417
        # MPEG audio sync word: 0xFF 0xFB
        assert audio.startswith(b"\xff\xfb")

    def test_generate_minimal_wav_validity(self) -> None:
        """Verify WAV generator produces valid 44-byte RIFF WAVE header."""
        audio = generate_minimal_audio_bytes(duration_ms=500, format="wav")
        assert isinstance(audio, bytes)
        assert len(audio) > 44
        assert audio.startswith(b"RIFF")
        assert b"WAVE" in audio[:12]
        assert b"fmt " in audio[:20]
        assert b"data" in audio[:40]


# ===========================================================================
# 5. TTSService Core Synthesis & Lifecycle Tests
# ===========================================================================

class TestTTSServiceCore:
    """Test suite for TTSService synthesis execution, cloud mock, and fallback."""

    @pytest.mark.asyncio
    async def test_synthesize_empty_text_returns_none(self) -> None:
        """Verify empty or whitespace-only text returns None."""
        service = TTSService(api_key="mock-key")
        assert await service.synthesize("") is None
        assert await service.synthesize("   ") is None
        await service.close()

    @pytest.mark.asyncio
    async def test_synthesize_without_api_key_default_returns_none(self) -> None:
        """Verify synthesis without API key returns None by default (backward compatibility)."""
        service = TTSService(api_key="")
        result = await service.synthesize("Kukuku... Morumotto-kun!")
        assert result is None
        await service.close()

    @pytest.mark.asyncio
    async def test_synthesize_without_api_key_with_fallback_synthetic(self) -> None:
        """Verify synthesis with fallback_synthetic=True returns valid audio bytes."""
        service = TTSService(api_key="")
        result = await service.synthesize(
            "Kukuku... Morumotto-kun!",
            fallback_synthetic=True,
        )
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0
        await service.close()

    @pytest.mark.asyncio
    async def test_synthesize_cloud_success_mock(self) -> None:
        """Verify successful remote Featherless TTS invocation with Kokoro-82M."""
        fake_audio = b"\xff\xfb\x90\x00_KOKORO_SYNTHESIZED_AUDIO_BYTES_"
        service = TTSService(api_key="valid-test-key")

        mock_resp = HttpxResponse(200, content=fake_audio)
        with patch.object(service._client, "post", new=AsyncMock(return_value=mock_resp)) as mock_post:
            audio = await service.synthesize(
                text="The experiment is a success, Morumotto-kun!",
                voice="jf_nezumi",
                speed=1.10,
                mood="flow",
            )
            assert audio == fake_audio
            mock_post.assert_awaited_once()

            # Verify request payload
            call_kwargs = mock_post.await_args.kwargs
            payload = call_kwargs["json"]
            assert payload["model"] == "hexgrad/Kokoro-82M"
            assert payload["voice"] == "jf_nezumi"
            assert payload["response_format"] == "mp3"
            assert "voice_mix" in payload
            assert "jf_nezumi" in payload["voice_mix"]
            assert payload["voice_mix"]["jf_nezumi"] >= 0.60

        await service.close()

    @pytest.mark.asyncio
    async def test_synthesize_cloud_api_error_graceful_fallback(self) -> None:
        """Verify network/server failure falls back gracefully without raising exceptions."""
        service = TTSService(api_key="valid-test-key")

        # Mock 500 server error
        error_resp = HttpxResponse(500, content=b"Internal Server Error")
        with patch.object(service._client, "post", new=AsyncMock(return_value=error_resp)):
            # Without fallback: returns None
            result_none = await service.synthesize("Test speech", fallback_synthetic=False)
            assert result_none is None

            # With fallback: returns synthetic audio bytes
            result_audio = await service.synthesize("Test speech", fallback_synthetic=True)
            assert result_audio is not None
            assert len(result_audio) > 0

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_voice_orchestration(self) -> None:
        """Verify high-level generate_voice returns complete structured payload."""
        service = TTSService(api_key="")
        result = await service.generate_voice(
            text="Observe the architectural beauty of our microservices!",
            mood="happy",
            voice="jf_nezumi",
            fallback_synthetic=True,
        )

        assert result["audio_bytes"] is not None
        assert result["audio_base64"] is not None
        # Verify valid base64
        decoded = base64.b64decode(result["audio_base64"])
        assert decoded == result["audio_bytes"]

        assert result["media_type"] == "audio/mpeg"
        assert len(result["subtitle_cue"]) > 0
        assert len(result["romanized_callout"]) > 0
        assert len(result["japanese_speech_text"]) > 0
        assert result["english_text"] == "Observe the architectural beauty of our microservices!"
        assert result["mood"] == "happy"
        assert result["voice"] == "jf_nezumi"
        assert result["device"] == "cpu"
        assert result["vram_allocated_mb"] == 0.0

        await service.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Verify TTSService works cleanly as an async context manager."""
        async with TTSService() as service:
            assert service.get_device() == "cpu"
            assert service._client.is_closed is False
        assert service._client.is_closed is True


# ===========================================================================
# 6. FastAPI Router Endpoint Tests
# ===========================================================================

class TestTTSRouterEndpoints:
    """Test suite for FastAPI TTS router endpoints in app.routers.tts."""

    def test_get_guardrails_endpoint(self, client: TestClient) -> None:
        """Test GET /api/tts/guardrails returns 200 and low-VRAM safety confirmation."""
        resp = client.get("/api/tts/guardrails")
        assert resp.status_code == 200
        data = resp.json()
        assert data["device"] == "cpu"
        assert data["vram_limit_mb"] == 2048.0
        assert data["vram_allocated_mb"] == 0.0
        assert "AMD Radeon HD 5450" in data["target_hardware"]
        assert data["guardrail_active"] is True

    def test_get_voices_endpoint(self, client: TestClient) -> None:
        """Test GET /api/tts/voices returns available Kokoro voice list and Tachyon blend."""
        resp = client.get("/api/tts/voices")
        assert resp.status_code == 200
        data = resp.json()
        assert "voices" in data
        assert len(data["voices"]) >= 5
        voice_ids = [v["id"] for v in data["voices"]]
        assert "jf_nezumi" in voice_ids
        assert "jf_alpha" in voice_ids
        assert data["default_voice"] == "jf_nezumi"
        assert "tachyon_mix" in data

    def test_get_health_endpoint(self, client: TestClient) -> None:
        """Test GET /api/tts/health returns 200 with service and device status."""
        resp = client.get("/api/tts/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["device"] == "cpu"

    def test_post_generate_json_response(self, client: TestClient) -> None:
        """Test POST /api/tts/generate returns structured JSON with base64 audio and subtitle cues."""
        payload = {
            "text": "Refactoring technical debt with pharmacokinetic precision!",
            "mood": "serious",
            "voice": "jf_nezumi",
            "fallback_synthetic": True,
        }
        resp = client.post("/api/tts/generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["audio_base64"] is not None
        assert data["media_type"] == "audio/mpeg"
        assert len(data["subtitle_cue"]) > 0
        assert len(data["japanese_speech_text"]) > 0
        assert data["english_text"] == payload["text"]
        assert data["mood"] == "serious"
        assert data["device"] == "cpu"
        assert data["vram_allocated_mb"] == 0.0

    def test_post_generate_stream_response(self, client: TestClient) -> None:
        """Test POST /api/tts/generate with stream=True returns raw audio stream with headers."""
        payload = {
            "text": "Aha! Witness the light of my formula!",
            "mood": "flow",
            "voice": "jf_nezumi",
            "stream": True,
            "fallback_synthetic": True,
        }
        resp = client.post("/api/tts/generate", json=payload)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/mpeg"
        assert "X-Subtitle-Cue" in resp.headers
        assert resp.headers["X-Device"] == "cpu"
        assert resp.headers["X-Mood"] == "flow"
        assert len(resp.content) > 0

    def test_post_synthesize_endpoint_success(self, client: TestClient) -> None:
        """Test POST /api/tts/synthesize returns direct audio/mpeg response."""
        payload = {
            "text": "Energy levels restored, Morumotto-kun!",
            "voice": "jf_nezumi",
            "speed": 1.04,
            "mood": "happy",
            "fallback_synthetic": True,
        }
        resp = client.post("/api/tts/synthesize", json=payload)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/mpeg"
        assert "X-Subtitle-Cue" in resp.headers
        assert resp.headers["X-Device"] == "cpu"
        assert len(resp.content) > 0

    def test_post_synthesize_empty_text_returns_204(self, client: TestClient) -> None:
        """Test POST /api/tts/synthesize with empty text returns 204 No Content."""
        payload = {
            "text": "",
            "voice": "jf_nezumi",
            "fallback_synthetic": False,
        }
        resp = client.post("/api/tts/synthesize", json=payload)
        assert resp.status_code == 204

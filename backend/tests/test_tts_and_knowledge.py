"""Tests for TTSService and KnowledgeService."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response as HttpxResponse

from app.models.schemas import AttributeType
from app.services.knowledge_service import KnowledgeService
from app.services.tts_service import TTSService


@pytest.mark.asyncio
async def test_tts_without_api_key_returns_none() -> None:
    tts = TTSService(api_key="")
    audio = await tts.synthesize("Kukuku... Morumotto-kun!")
    assert audio is None
    await tts.close()


@pytest.mark.asyncio
async def test_tts_successful_synthesis() -> None:
    fake_audio = b"\xff\xfb\x90\x00FAKE_MP3_BYTES"
    tts = TTSService(api_key="valid-test-key")

    mock_resp = HttpxResponse(200, content=fake_audio)
    with patch.object(tts._client, "post", new=AsyncMock(return_value=mock_resp)) as mock_post:
        audio = await tts.synthesize("Kukuku... Test speech!", voice="af_bella")
        assert audio == fake_audio
        mock_post.assert_awaited_once()

    await tts.close()


def test_knowledge_curriculum_coverage() -> None:
    for attr in AttributeType:
        card = KnowledgeService.get_curriculum(attr)
        assert "title" in card
        assert "primary_pattern" in card
        assert "cutscene" in card
        assert "description" in card["cutscene"]

        context = KnowledgeService.enrich_training_context(attr)
        assert len(context) > 20
        assert card["primary_pattern"] in context

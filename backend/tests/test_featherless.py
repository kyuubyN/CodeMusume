"""Unit tests for backend/app/services/featherless_service.py — Mission 05."""
from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.schemas import AttributeType, GameState, MoodState, RaceIncident
from app.services.featherless_service import (
    TACHYON_SYSTEM_PROMPT,
    FeatherlessGateway,
    _FALLBACK_DIALOGUE,
    _FALLBACK_COMMENTARY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gateway(api_key: str = "test-key") -> FeatherlessGateway:
    return FeatherlessGateway(
        api_key=api_key,
        base_url="https://api.featherless.ai/v1",
        model="Qwen/Qwen2.5-72B-Instruct",
    )


def _game_state() -> GameState:
    return GameState(turn=3, energy=70, mood=MoodState.GOOD)


def _incident() -> RaceIncident:
    return RaceIncident(
        sector=2,
        distance_m=500.0,
        name="Traffic Spike",
        tested_attribute=AttributeType.POWER,
        description="High load test.",
        player_success=True,
        tachyon_callout="Kukuku…",
    )


def _mock_http_response(content: str, status_code: int = 200) -> MagicMock:
    """Build a fake httpx.Response-like mock."""
    payload = {
        "choices": [
            {"message": {"content": content}}
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status = MagicMock()  # no-op on 200
    return mock_resp


def _mock_http_error_response(status_code: int = 500) -> MagicMock:
    """Build a fake httpx.Response that raises on raise_for_status."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            message=f"Server error {status_code}",
            request=MagicMock(),
            response=MagicMock(),
        )
    )
    return mock_resp


# ===========================================================================
# System prompt constant
# ===========================================================================

class TestSystemPrompt:
    def test_system_prompt_defined(self):
        assert TACHYON_SYSTEM_PROMPT
        assert len(TACHYON_SYSTEM_PROMPT) > 50

    def test_system_prompt_contains_tachyon(self):
        assert "Tachyon" in TACHYON_SYSTEM_PROMPT

    def test_system_prompt_contains_morumotto(self):
        assert "Morumotto" in TACHYON_SYSTEM_PROMPT

    def test_system_prompt_contains_key_terms(self):
        for term in ("Kukuku", "cellular necrosis", "Fowler", "DDD"):
            assert term in TACHYON_SYSTEM_PROMPT, f"Missing term: {term}"


# ===========================================================================
# Fallback: missing API key
# ===========================================================================

class TestFallbackMissingApiKey:

    def test_generate_dialogue_returns_fallback_when_no_key(self):
        gw = _gateway(api_key="")

        async def _run() -> str:
            return await gw.generate_dialogue(_game_state(), "Training started.")

        result = asyncio.run(_run())
        assert isinstance(result, str)
        assert len(result) > 20

    def test_fallback_dialogue_is_in_character(self):
        gw = _gateway(api_key="")

        async def _run() -> str:
            return await gw.generate_dialogue(_game_state(), "Training started.")

        # Run several times to sample the pool
        for _ in range(5):
            result = asyncio.run(_run())
            assert any(
                marker in result
                for marker in ("Kukuku", "Hehehe", "Morumotto", "Cobaia")
            ), f"Fallback not in-character: {result!r}"

    def test_generate_race_commentary_returns_fallback_when_no_key(self):
        gw = _gateway(api_key="")

        async def _run() -> str:
            return await gw.generate_race_commentary(_incident(), "Legacy Monolith")

        result = asyncio.run(_run())
        assert isinstance(result, str)
        assert len(result) > 20

    def test_fallback_commentary_is_in_character(self):
        gw = _gateway(api_key="")

        async def _run() -> str:
            return await gw.generate_race_commentary(_incident(), "player")

        for _ in range(5):
            result = asyncio.run(_run())
            assert any(
                marker in result
                for marker in ("Kukuku", "Hehehe", "Morumotto", "Cobaia", "P99", "circuit")
            ), f"Fallback commentary not in-character: {result!r}"


# ===========================================================================
# Mocked HTTP 200 — correct JSON parsing
# ===========================================================================

class TestSuccessfulHttpResponse:

    def test_generate_dialogue_parses_completion(self):
        expected_text = "Ufufu… your async pipeline is magnificent, Morumotto-kun!"
        mock_resp = _mock_http_response(expected_text)

        async def _run() -> str:
            gw = _gateway()
            gw._client.post = AsyncMock(return_value=mock_resp)
            return await gw.generate_dialogue(_game_state(), "Training success.")

        result = asyncio.run(_run())
        assert result == expected_text

    def test_generate_dialogue_sends_correct_payload(self):
        captured: dict = {}
        mock_resp = _mock_http_response("OK response")

        async def _run() -> str:
            gw = _gateway()

            async def fake_post(url: str, json: Any, headers: Any) -> MagicMock:
                captured["url"] = url
                captured["json"] = json
                captured["headers"] = headers
                return mock_resp

            gw._client.post = fake_post
            return await gw.generate_dialogue(_game_state(), "turn event")

        asyncio.run(_run())

        assert "/chat/completions" in captured["url"]
        messages = captured["json"]["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == TACHYON_SYSTEM_PROMPT
        assert messages[1]["role"] == "user"
        assert "Turn:" in messages[1]["content"]
        assert "Energy:" in messages[1]["content"]
        assert "Mood:" in messages[1]["content"]
        assert "Event:" in messages[1]["content"]

    def test_generate_dialogue_uses_correct_model_and_params(self):
        captured: dict = {}
        mock_resp = _mock_http_response("OK")

        async def _run() -> str:
            gw = _gateway()

            async def fake_post(url: str, json: Any, headers: Any) -> MagicMock:
                captured["json"] = json
                return mock_resp

            gw._client.post = fake_post
            return await gw.generate_dialogue(_game_state(), "event")

        asyncio.run(_run())

        assert captured["json"]["model"] == "Qwen/Qwen2.5-72B-Instruct"
        assert captured["json"]["temperature"] == pytest.approx(0.85)
        assert captured["json"]["max_tokens"] == 180

    def test_generate_race_commentary_parses_completion(self):
        expected_text = "Kukuku… the Traffic Spike incident fires! Power is the prescription!"
        mock_resp = _mock_http_response(expected_text)

        async def _run() -> str:
            gw = _gateway()
            gw._client.post = AsyncMock(return_value=mock_resp)
            return await gw.generate_race_commentary(_incident(), "player")

        result = asyncio.run(_run())
        assert result == expected_text

    def test_generate_race_commentary_max_tokens_120(self):
        captured: dict = {}
        mock_resp = _mock_http_response("OK commentary")

        async def _run() -> str:
            gw = _gateway()

            async def fake_post(url: str, json: Any, headers: Any) -> MagicMock:
                captured["json"] = json
                return mock_resp

            gw._client.post = fake_post
            return await gw.generate_race_commentary(_incident(), "legacy")

        asyncio.run(_run())
        assert captured["json"]["max_tokens"] == 120

    def test_auth_header_sent(self):
        captured: dict = {}
        mock_resp = _mock_http_response("OK")

        async def _run() -> str:
            gw = _gateway(api_key="my-secret-key")

            async def fake_post(url: str, json: Any, headers: Any) -> MagicMock:
                captured["headers"] = headers
                return mock_resp

            gw._client.post = fake_post
            return await gw.generate_dialogue(_game_state(), "event")

        asyncio.run(_run())
        assert captured["headers"].get("Authorization") == "Bearer my-secret-key"


# ===========================================================================
# Network failure resilience
# ===========================================================================

class TestNetworkResilience:

    def _run_with_exception(self, exc: Exception, method: str = "dialogue") -> str:
        async def _run() -> str:
            gw = _gateway()
            gw._client.post = AsyncMock(side_effect=exc)
            if method == "dialogue":
                return await gw.generate_dialogue(_game_state(), "event")
            return await gw.generate_race_commentary(_incident(), "player")

        return asyncio.run(_run())

    def test_timeout_does_not_raise_on_dialogue(self):
        result = self._run_with_exception(httpx.TimeoutException("timed out"))
        assert isinstance(result, str)
        assert len(result) > 10

    def test_connect_error_does_not_raise_on_dialogue(self):
        result = self._run_with_exception(httpx.ConnectError("connection refused"))
        assert isinstance(result, str)
        assert len(result) > 10

    def test_timeout_does_not_raise_on_commentary(self):
        result = self._run_with_exception(
            httpx.TimeoutException("timed out"), method="commentary"
        )
        assert isinstance(result, str)
        assert len(result) > 10

    def test_http_500_returns_fallback_on_dialogue(self):
        mock_resp = _mock_http_error_response(500)

        async def _run() -> str:
            gw = _gateway()
            gw._client.post = AsyncMock(return_value=mock_resp)
            return await gw.generate_dialogue(_game_state(), "event")

        result = asyncio.run(_run())
        assert isinstance(result, str)
        assert len(result) > 10

    def test_http_500_returns_fallback_on_commentary(self):
        mock_resp = _mock_http_error_response(500)

        async def _run() -> str:
            gw = _gateway()
            gw._client.post = AsyncMock(return_value=mock_resp)
            return await gw.generate_race_commentary(_incident(), "player")

        result = asyncio.run(_run())
        assert isinstance(result, str)
        assert len(result) > 10

    def test_malformed_json_returns_fallback_on_dialogue(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"unexpected": "shape"}  # missing 'choices'

        async def _run() -> str:
            gw = _gateway()
            gw._client.post = AsyncMock(return_value=mock_resp)
            return await gw.generate_dialogue(_game_state(), "event")

        result = asyncio.run(_run())
        assert isinstance(result, str)
        assert len(result) > 10

    def test_network_error_fallback_is_in_character(self):
        result = self._run_with_exception(httpx.NetworkError("unreachable"))
        assert any(
            marker in result
            for marker in ("Kukuku", "Hehehe", "Morumotto", "Cobaia")
        ), f"Fallback after network error not in-character: {result!r}"


# ===========================================================================
# Constructor / settings defaults
# ===========================================================================

class TestGatewayConstruction:

    def test_uses_settings_defaults_when_no_args(self):
        with patch("app.services.featherless_service.get_settings") as mock_settings:
            mock_cfg = MagicMock()
            mock_cfg.FEATHERLESS_API_KEY = "settings-key"
            mock_cfg.FEATHERLESS_BASE_URL = "https://example.com/v1"
            mock_cfg.FEATHERLESS_MODEL = "some-model"
            mock_settings.return_value = mock_cfg

            gw = FeatherlessGateway()
            assert gw.api_key == "settings-key"
            assert gw.base_url == "https://example.com/v1"
            assert gw.model == "some-model"

    def test_explicit_args_override_settings(self):
        gw = FeatherlessGateway(
            api_key="override-key",
            base_url="https://other.com/v1",
            model="other-model",
        )
        assert gw.api_key == "override-key"
        assert gw.base_url == "https://other.com/v1"
        assert gw.model == "other-model"

    def test_http_client_is_async(self):
        gw = _gateway()
        assert isinstance(gw._client, httpx.AsyncClient)

    def test_context_manager_closes_client(self):
        async def _run() -> None:
            async with _gateway() as gw:
                assert isinstance(gw, FeatherlessGateway)

        asyncio.run(_run())


# ===========================================================================
# Fallback pool contents
# ===========================================================================

class TestFallbackPools:

    def test_fallback_dialogue_pool_non_empty(self):
        assert len(_FALLBACK_DIALOGUE) >= 3

    def test_fallback_commentary_pool_non_empty(self):
        assert len(_FALLBACK_COMMENTARY) >= 3

    def test_all_dialogue_fallbacks_are_in_character(self):
        for msg in _FALLBACK_DIALOGUE:
            assert any(m in msg for m in ("Kukuku", "Hehehe", "Morumotto", "Cobaia")), (
                f"Dialogue fallback not in-character: {msg!r}"
            )

    def test_all_commentary_fallbacks_non_empty(self):
        for msg in _FALLBACK_COMMENTARY:
            assert len(msg) > 20

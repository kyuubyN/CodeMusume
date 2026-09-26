"""Integration tests for backend/app/main.py and backend/app/api/endpoints.py — Mission 06."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    AttributeType,
    AvatarPose,
    GameState,
    MoodState,
    RaceTick,
    RestResult,
    TrainResult,
)
from app.services.trainer_service import TrainerEngine

# ---------------------------------------------------------------------------
# Shared client (module-scoped so state accumulates across test ordering)
# We reset the singleton before each class that depends on a clean state.
# ---------------------------------------------------------------------------

client = TestClient(app, raise_server_exceptions=True)


def _reset_state() -> None:
    """Reset the in-memory engine singleton to a fresh GameState."""
    import app.api.endpoints as ep
    ep._engine = TrainerEngine()


# ===========================================================================
# Health check
# ===========================================================================

class TestHealth:
    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_body(self):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["app"] == "CodeMusume"


# ===========================================================================
# GET /api/state
# ===========================================================================

class TestGetState:
    def setup_method(self):
        _reset_state()

    def test_returns_200(self):
        resp = client.get("/api/state")
        assert resp.status_code == 200

    def test_returns_valid_game_state_shape(self):
        resp = client.get("/api/state")
        data = resp.json()
        assert "turn" in data
        assert "energy" in data
        assert "mood" in data
        assert "attributes" in data
        assert "is_game_over" in data

    def test_default_state_values(self):
        resp = client.get("/api/state")
        data = resp.json()
        assert data["turn"] == 1
        assert data["energy"] == 100
        assert data["mood"] == MoodState.NORMAL.value
        assert data["is_game_over"] is False

    def test_attributes_shape(self):
        resp = client.get("/api/state")
        attrs = resp.json()["attributes"]
        for key in ("speed", "stamina", "power", "guts", "wisdom"):
            assert key in attrs
            assert isinstance(attrs[key], int)


# ===========================================================================
# POST /api/scan
# ===========================================================================

class TestScan:
    def setup_method(self):
        _reset_state()

    def test_scan_returns_200(self):
        resp = client.post("/api/scan", json={"target_path": "."})
        assert resp.status_code == 200

    def test_scan_returns_game_state(self):
        resp = client.post("/api/scan", json={"target_path": "."})
        data = resp.json()
        assert "attributes" in data
        assert "turn" in data

    def test_scan_invalid_path_falls_back_to_cwd(self):
        resp = client.post("/api/scan", json={"target_path": "/nonexistent/path/xyz"})
        assert resp.status_code == 200  # must not 500; falls back to "."

    def test_scan_sets_attributes_on_engine(self):
        client.post("/api/scan", json={"target_path": "."})
        state_resp = client.get("/api/state")
        data = state_resp.json()
        # After a scan the attributes are real scanner output (not defaults)
        attrs = data["attributes"]
        total = sum(attrs[k] for k in ("speed", "stamina", "power", "guts", "wisdom"))
        assert total > 0

    def test_scan_default_body(self):
        """POST with no body should work (default target_path='.')."""
        resp = client.post("/api/scan")
        assert resp.status_code == 200


# ===========================================================================
# POST /api/train
# ===========================================================================

class TestTrain:
    def setup_method(self):
        _reset_state()

    def _train(self, attribute: str = "speed") -> dict:
        # Patch the gateway so we don't make real HTTP calls
        with patch(
            "app.api.endpoints._gateway.generate_dialogue",
            new_callable=AsyncMock,
            return_value="Kukuku… splendid, Morumotto-kun!",
        ):
            resp = client.post("/api/train", json={"attribute": attribute})
        assert resp.status_code == 200
        return resp.json()

    def test_train_returns_200(self):
        self._train()

    def test_train_returns_train_result_shape(self):
        data = self._train()
        for field in ("success", "attribute", "stat_gained", "energy_spent",
                      "failure_rate", "tachyon_commentary", "pose", "updated_state"):
            assert field in data, f"Missing field: {field}"

    def test_train_increments_turn(self):
        data = self._train()
        assert data["updated_state"]["turn"] == 2

    def test_train_decreases_energy(self):
        data = self._train()
        # Energy should drop by 15 (fail) or 20 (success)
        assert data["updated_state"]["energy"] < 100

    def test_train_modifies_engine_state(self):
        self._train()
        state_resp = client.get("/api/state")
        assert state_resp.json()["turn"] == 2

    def test_train_uses_live_commentary(self):
        data = self._train()
        assert data["tachyon_commentary"] == "Kukuku… splendid, Morumotto-kun!"

    def test_train_all_attributes(self):
        for attr in ("speed", "stamina", "power", "guts", "wisdom"):
            _reset_state()
            data = self._train(attr)
            assert data["attribute"] == attr

    def test_train_invalid_attribute_returns_422(self):
        resp = client.post("/api/train", json={"attribute": "nonexistent"})
        assert resp.status_code == 422


# ===========================================================================
# POST /api/rest
# ===========================================================================

class TestRest:
    def setup_method(self):
        _reset_state()
        # Drain some energy first via a successful train
        with patch(
            "app.api.endpoints._gateway.generate_dialogue",
            new_callable=AsyncMock,
            return_value="commentary",
        ):
            client.post("/api/train", json={"attribute": "speed"})

    def test_rest_returns_200(self):
        resp = client.post("/api/rest")
        assert resp.status_code == 200

    def test_rest_returns_rest_result_shape(self):
        resp = client.post("/api/rest")
        data = resp.json()
        for field in ("energy_recovered", "new_mood", "tachyon_commentary", "updated_state"):
            assert field in data, f"Missing field: {field}"

    def test_rest_increments_turn(self):
        state_before = client.get("/api/state").json()
        turn_before = state_before["turn"]
        resp = client.post("/api/rest")
        assert resp.json()["updated_state"]["turn"] == turn_before + 1

    def test_rest_recovers_energy(self):
        energy_before = client.get("/api/state").json()["energy"]
        resp = client.post("/api/rest")
        energy_after = resp.json()["updated_state"]["energy"]
        assert energy_after >= energy_before  # rest never decreases energy

    def test_rest_updates_engine_state(self):
        turn_before = client.get("/api/state").json()["turn"]
        client.post("/api/rest")
        turn_after = client.get("/api/state").json()["turn"]
        assert turn_after == turn_before + 1


# ===========================================================================
# POST /api/race/simulate
# ===========================================================================

class TestRaceSimulate:
    def setup_method(self):
        _reset_state()

    def test_returns_200(self):
        resp = client.post("/api/race/simulate")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.post("/api/race/simulate")
        data = resp.json()
        assert isinstance(data, list)

    def test_returns_100_ticks(self):
        resp = client.post("/api/race/simulate")
        data = resp.json()
        assert len(data) == 100

    def test_each_tick_has_required_fields(self):
        resp = client.post("/api/race/simulate")
        ticks = resp.json()
        for tick in ticks:
            assert "tick" in tick
            assert "distance_m" in tick
            assert "player_distance" in tick
            assert "rivals" in tick
            assert "is_finished" in tick

    def test_last_tick_is_finished(self):
        resp = client.post("/api/race/simulate")
        ticks = resp.json()
        assert ticks[-1]["is_finished"] is True

    def test_tick_numbers_sequential(self):
        resp = client.post("/api/race/simulate")
        ticks = resp.json()
        for i, tick in enumerate(ticks):
            assert tick["tick"] == i + 1

    def test_each_tick_has_two_rivals(self):
        resp = client.post("/api/race/simulate")
        ticks = resp.json()
        for tick in ticks:
            assert len(tick["rivals"]) == 2


# ===========================================================================
# GET /api/race/stream (SSE)
# ===========================================================================

class TestRaceStream:
    def setup_method(self):
        _reset_state()

    def test_returns_200(self):
        with client.stream("GET", "/api/race/stream") as resp:
            assert resp.status_code == 200

    def test_content_type_is_event_stream(self):
        with client.stream("GET", "/api/race/stream") as resp:
            ct = resp.headers.get("content-type", "")
            assert "text/event-stream" in ct

    def test_stream_emits_data_lines(self):
        lines: list[str] = []
        with client.stream("GET", "/api/race/stream") as resp:
            for line in resp.iter_lines():
                lines.append(line)
                if len(lines) >= 5:
                    break
        data_lines = [l for l in lines if l.startswith("data:")]
        assert len(data_lines) >= 1

    def test_stream_first_tick_is_valid_json(self):
        with client.stream("GET", "/api/race/stream") as resp:
            for line in resp.iter_lines():
                if line.startswith("data:") and "[DONE]" not in line:
                    payload = json.loads(line[len("data:"):].strip())
                    assert "tick" in payload
                    assert "player_distance" in payload
                    break


# ===========================================================================
# POST /api/dialogue
# ===========================================================================

class TestDialogue:
    def setup_method(self):
        _reset_state()

    def test_returns_200(self):
        with patch(
            "app.api.endpoints._gateway.generate_dialogue",
            new_callable=AsyncMock,
            return_value="Kukuku… fascinating, Morumotto-kun!",
        ):
            resp = client.post("/api/dialogue", json={"event": "Training started."})
        assert resp.status_code == 200

    def test_returns_dialogue_and_pose(self):
        with patch(
            "app.api.endpoints._gateway.generate_dialogue",
            new_callable=AsyncMock,
            return_value="Kukuku… fascinating, Morumotto-kun!",
        ):
            resp = client.post("/api/dialogue", json={"event": "Training started."})
        data = resp.json()
        assert "dialogue" in data
        assert "pose" in data

    def test_dialogue_content_returned(self):
        with patch(
            "app.api.endpoints._gateway.generate_dialogue",
            new_callable=AsyncMock,
            return_value="Kukuku… fascinating, Morumotto-kun!",
        ):
            resp = client.post("/api/dialogue", json={"event": "turn event"})
        assert resp.json()["dialogue"] == "Kukuku… fascinating, Morumotto-kun!"

    def test_pose_is_valid_avatar_pose(self):
        valid_poses = {p.value for p in AvatarPose}
        with patch(
            "app.api.endpoints._gateway.generate_dialogue",
            new_callable=AsyncMock,
            return_value="commentary",
        ):
            resp = client.post("/api/dialogue", json={"event": "anything"})
        assert resp.json()["pose"] in valid_poses

    def test_missing_event_returns_422(self):
        resp = client.post("/api/dialogue", json={})
        assert resp.status_code == 422

    def test_dialogue_fallback_when_no_api_key(self):
        """Without patching, the gateway has no key and falls back gracefully."""
        resp = client.post("/api/dialogue", json={"event": "test fallback"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["dialogue"]) > 10


# ===========================================================================
# CORS headers
# ===========================================================================

class TestCORS:
    def test_options_request_returns_cors_headers(self):
        resp = client.options(
            "/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        # CORS middleware should add the header
        assert resp.headers.get("access-control-allow-origin") is not None

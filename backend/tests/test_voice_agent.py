"""Tests for the AssemblyAI Voice Agent integration: session config, tools, rescan."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import endpoints as ep
from app.main import app
from app.models.schemas import AttributeType
from app.services.voice_agent_service import (
    VOICE_TOOLS,
    build_session_config,
    dispatch_tool,
)

SAMPLE_REPO = Path(__file__).resolve().parents[2] / "sample_trainee_repo"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    dest = tmp_path / "trainee"
    shutil.copytree(SAMPLE_REPO, dest)
    return dest


@pytest.fixture
def engine(repo: Path):
    return ep.scan_into_engine(str(repo))


def test_scan_tracks_numbered_smells(engine):
    assert engine.smells
    assert [s.id for s in engine.smells] == list(range(1, len(engine.smells) + 1))
    assert all(not s.file_path.startswith("/") for s in engine.smells)


def test_open_smells_are_worst_first(engine):
    first = engine.open_smells()[0]
    # the unclosed log file: the CFG dataflow rule replaces the per-file STAMINA-001
    assert first.rule_id == "STAMINA-004"
    assert first.id == 1


def test_session_config_shape(engine):
    cfg = build_session_config(engine)
    assert "Morumotto-kun" in cfg["system_prompt"]
    assert "legacy_service.py" in cfg["system_prompt"]
    assert f"{len(engine.open_smells())} ailments" in cfg["greeting"]
    assert cfg["tools"] == VOICE_TOOLS
    assert len(VOICE_TOOLS) <= 20
    for tool in VOICE_TOOLS:
        assert tool["type"] == "function"
        assert tool["parameters"]["type"] == "object"
    assert "legacy_service.py" in cfg["input"]["keyterms"]


def test_open_unknown_smell_returns_error(engine):
    out = dispatch_tool(engine, "open_smell", {"smell_id": 999})
    assert "error" in out.result
    assert out.ui == {}


def test_train_drills_real_smell(engine, monkeypatch):
    monkeypatch.setattr("random.random", lambda: 0.99)  # never fail
    before = engine.state.attributes.guts
    out = dispatch_tool(engine, "train", {"attribute": "guts"})
    assert out.result["success"]
    assert out.result["drilled_smell"]["stat"] == "guts"
    assert engine.state.attributes.guts == before + out.result["gained"]
    assert all(s.attribute != AttributeType.GUTS or s.drilled or s.id != out.ui["smell_id"] for s in engine.smells)


def test_train_by_smell_uses_its_attribute(engine, monkeypatch):
    monkeypatch.setattr("random.random", lambda: 0.99)
    speed_smell = next(s for s in engine.smells if s.attribute == AttributeType.SPEED)
    out = dispatch_tool(engine, "train", {"attribute": "wisdom", "smell_id": speed_smell.id})
    assert out.result["stat"] == "speed"
    assert engine.get_smell(speed_smell.id).drilled


def test_start_race_locked_then_unlocked(engine, monkeypatch):
    monkeypatch.setattr("random.random", lambda: 0.99)
    assert "error" in dispatch_tool(engine, "start_race", {}).result
    for _ in range(engine.state.interactions_required):
        dispatch_tool(engine, "train", {"attribute": "power"})
    out = dispatch_tool(engine, "start_race", {})
    assert out.ui == {"view": "race"}


def test_rescan_detects_real_fix_and_keeps_training_bonus(engine, repo, monkeypatch):
    monkeypatch.setattr("random.random", lambda: 0.99)
    dispatch_tool(engine, "train", {"attribute": "stamina"})
    trained_bonus = engine.training_bonus["stamina"]
    base_before = engine.base_attributes.stamina
    ids_before = {s.key: s.id for s in engine.smells}

    src = repo / "legacy_service.py"
    code = src.read_text()
    code = code.replace(
        '    log_file = open("orders.log", "a")\n    log_file.write(f"Processing {len(order_ids)} orders\\n")',
        '    with open("orders.log", "a") as log_file:\n        log_file.write(f"Processing {len(order_ids)} orders\\n")',
    )
    src.write_text(code)

    out = dispatch_tool(engine, "rescan_repo", {})
    assert [s["stat"] for s in out.result["fixed"]] == ["stamina"]
    assert out.result["stat_changes"]["stamina"] > 0
    assert engine.base_attributes.stamina > base_before
    assert engine.state.attributes.stamina == engine.base_attributes.stamina + trained_bonus
    # Surviving smells keep the ids the trainer has been hearing
    for s in engine.smells:
        assert ids_before[s.key] == s.id


def test_voice_routes():
    with TestClient(app) as client:
        client.post("/api/scan", json={"target_path": str(SAMPLE_REPO)})
        assert client.get("/api/voice/session").json()["tools"]
        assert "Live state" in client.get("/api/voice/prompt").json()["system_prompt"]
        assert client.get("/api/smells").json()
        assert client.get("/api/smells/1/prescription").status_code == 200
        assert client.get("/api/smells/999/prescription").status_code == 404
        resp = client.post("/api/voice/tool", json={"name": "list_smells", "arguments": {}})
        assert resp.json()["ui"]["panel"] == "smells"
        assert client.post("/api/voice/tool", json={"name": "answer_quiz"}).status_code == 400
        assert client.post("/api/rescan").status_code == 200
        client.post("/api/voice/tool", json={"name": "rest", "arguments": {}})
        fresh = client.post("/api/reset").json()
        assert fresh["turn"] == 1 and fresh["repo_name"] == "sample_trainee_repo"


def test_token_without_key_is_503(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "ASSEMBLYAI_API_KEY", "")
    with TestClient(app) as client:
        assert client.get("/api/voice/token").status_code == 503

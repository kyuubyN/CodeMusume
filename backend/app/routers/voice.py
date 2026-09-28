"""Voice Agent API routes (token, session config, tool execution) and lab routes."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api import endpoints
from app.lab.findings import scan_repo_full
from app.lab.game import LabError
from app.models.schemas import CodeSmell, GameState, RaceTick, RescanResult
from app.services.race_service import RaceSimulator
from app.services.voice_agent_service import (
    CLIENT_TOOLS,
    ToolOutcome,
    VoiceNotConfigured,
    build_prescription,
    build_session_config,
    build_system_prompt,
    dispatch,
    mint_token,
)

router = APIRouter(prefix="/api")


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Voice agent
# ---------------------------------------------------------------------------

@router.get("/voice/token")
async def voice_token() -> dict[str, str]:
    """Mint a one-time browser token for the AssemblyAI Voice Agent WebSocket."""
    try:
        return {"token": await mint_token()}
    except VoiceNotConfigured as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    except httpx.HTTPStatusError as err:
        raise HTTPException(
            status_code=502,
            detail=f"AssemblyAI token request failed ({err.response.status_code}): {err.response.text[:200]}",
        ) from err
    except httpx.HTTPError as err:
        raise HTTPException(status_code=502, detail=f"AssemblyAI unreachable: {err}") from err


@router.get("/voice/session")
async def voice_session() -> dict[str, Any]:
    """Full inline session config for the first session.update."""
    return build_session_config(endpoints._get_engine(), endpoints.get_lab())


@router.get("/voice/prompt")
async def voice_prompt() -> dict[str, str]:
    """Fresh system prompt with the live game state, for mid-session updates."""
    return {"system_prompt": build_system_prompt(endpoints._get_engine(), endpoints.get_lab())}


@router.post("/voice/tool", response_model=ToolOutcome)
async def voice_tool(req: ToolCallRequest) -> ToolOutcome:
    """Execute one agent tool call (or an on-screen button) against the game."""
    if req.name in CLIENT_TOOLS:
        raise HTTPException(status_code=400, detail=f"'{req.name}' runs in the browser")
    return await dispatch(endpoints._get_engine(), endpoints.get_lab(), req.name, req.arguments)


# ---------------------------------------------------------------------------
# Free lab (your own repository)
# ---------------------------------------------------------------------------

@router.get("/smells", response_model=list[CodeSmell])
async def list_smells() -> list[CodeSmell]:
    """All tracked code smells (open and drilled)."""
    return endpoints._get_engine().smells


@router.get("/smells/{smell_id}/prescription")
async def smell_prescription(smell_id: int) -> dict[str, str]:
    smell = endpoints._get_engine().get_smell(smell_id)
    if smell is None:
        raise HTTPException(status_code=404, detail="Unknown smell")
    return {"prescription": build_prescription(smell)}


@router.post("/rescan", response_model=RescanResult)
async def rescan() -> RescanResult:
    """Re-scan the current repository and diff smells against the last scan."""
    engine = endpoints._get_engine()
    scores, detected = scan_repo_full(engine.repo_root)
    return engine.rescan(scores, detected, engine.repo_root)


@router.post("/reset", response_model=GameState)
async def reset() -> GameState:
    """Start a new season: a fresh career in the lab, or a fresh scan of your repo."""
    lab = endpoints.get_lab()
    if lab.mode == "lab":
        return (await endpoints.start_lab_career(fresh=True)).state
    return endpoints.scan_into_engine(endpoints._get_engine().repo_root).state


@router.get("/repo/report")
async def repo_report() -> dict[str, Any]:
    """Architecture standards check of the current trainee (your repo, or the lab specimen)."""
    import asyncio

    from app.lab.standards import build_report

    lab = endpoints.get_lab()
    root = lab.trainee.root if lab.mode == "lab" else endpoints._get_engine().repo_root
    return await asyncio.to_thread(build_report, root)


# ---------------------------------------------------------------------------
# Lab career
# ---------------------------------------------------------------------------

class CareerRequest(BaseModel):
    fresh: bool = False


class LabSnapshot(BaseModel):
    state: GameState
    lab: dict[str, Any]


def _snapshot() -> LabSnapshot:
    return LabSnapshot(state=endpoints._get_engine().state, lab=endpoints.get_lab().public_state())


@router.get("/lab", response_model=LabSnapshot)
async def lab_state() -> LabSnapshot:
    return _snapshot()


@router.post("/lab/career", response_model=LabSnapshot)
async def lab_career(req: CareerRequest = CareerRequest()) -> LabSnapshot:
    """Enter the lab: resume the current career, or start a fresh one."""
    await endpoints.start_lab_career(fresh=req.fresh)
    return _snapshot()


@router.post("/lab/close", response_model=LabSnapshot)
async def lab_close() -> LabSnapshot:
    """Dismiss a finished experiment debrief or an answered review."""
    lab = endpoints.get_lab()
    lab.close_experiment()
    lab.close_review()
    return _snapshot()


class DerbySetup(BaseModel):
    ticks: list[RaceTick]
    runners: list[dict[str, Any]]
    questions: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    attributes: dict[str, int]


@router.post("/lab/derby", response_model=DerbySetup)
async def lab_derby() -> DerbySetup:
    """Benchmark the trainee, then simulate the Derby against the rivals and your best ghost."""
    engine = endpoints._get_engine()
    lab = endpoints.get_lab()
    if lab.mode == "lab":
        if not engine.state.race_unlocked:
            raise HTTPException(status_code=409, detail="The Derby is locked.")
        from app.lab.harness.runner import run_all

        lab.results = await run_all(lab.trainee.root)
        attrs = lab.race_attributes()
    else:
        attrs = engine.state.attributes
    rivals = lab.rivals()
    ticks = RaceSimulator(player_attributes=attrs, rivals=rivals).run_simulation()
    questions = lab.derby_questions()
    return DerbySetup(
        ticks=ticks,
        runners=[{"id": "player", "name": engine.state.repo_name}] + [{"id": r.id, "name": r.name} for r in rivals],
        questions=[{"id": q.id, "concept": q.concept, "question": q.prompt, "code": q.code, "options": list(q.options)}
                   for q in questions],
        skills=lab.skills(),
        attributes=attrs.model_dump(),
    )


class CheckpointAnswer(BaseModel):
    question_id: str
    selected_index: int


@router.post("/lab/derby/answer")
async def lab_derby_answer(req: CheckpointAnswer) -> dict[str, Any]:
    try:
        return endpoints.get_lab().answer_checkpoint(req.question_id, req.selected_index)
    except LabError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


class DerbyResult(BaseModel):
    place: int
    checkpoint_score: int = 0


@router.post("/lab/derby/complete")
async def lab_derby_complete(req: DerbyResult) -> dict[str, Any]:
    """Finish the career: Hall of Fame entry, sparks for the next career, bond."""
    engine = endpoints._get_engine()
    lab = endpoints.get_lab()
    summary = lab.complete_career(engine, req.place, req.checkpoint_score)
    return {**summary, "state": engine.state.model_dump(), "lab": lab.public_state()}

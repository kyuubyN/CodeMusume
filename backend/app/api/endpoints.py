"""REST and SSE endpoints — all game services wired together."""
from __future__ import annotations

import asyncio
import json
import os
from typing import AsyncIterator

from fastapi import APIRouter, Body, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import BACKEND_DIR, PROJECT_ROOT, get_settings
from app.lab.findings import scan_repo_full
from app.lab.game import LabGame
from app.models.schemas import (
    DEFAULT_INITIAL_DIALOGUE,
    AttributeType,
    AvatarPose,
    MoodState,
    GameState,
    RaceTick,
    TrainRequest,
    TrainResult,
    RestResult,
    QuizQuestion,
    QuizEvaluationRequest,
    QuizEvaluationResponse,
    RaceCompleteRequest,
)
from app.services.featherless_service import FeatherlessGateway
from app.services.knowledge_service import KnowledgeService, memory_store
from app.services.mcp_research_service import McpResearchService
from app.services.quiz_service import QuizService
from app.services.race_service import RaceSimulator
from app.services.trainer_service import TrainerEngine
from app.services.tts_service import TTSService

router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# In-memory singleton state
# ---------------------------------------------------------------------------

_engine: TrainerEngine = TrainerEngine(GameState(dialogue=DEFAULT_INITIAL_DIALOGUE))
_gateway: FeatherlessGateway = FeatherlessGateway()
_tts: TTSService = TTSService()
_lab: LabGame | None = None


def _get_engine() -> TrainerEngine:
    return _engine


def get_lab() -> LabGame:
    global _lab
    if _lab is None:
        _lab = LabGame(get_settings().LAB_DATA_DIR)
    return _lab


def set_lab(lab: LabGame) -> None:
    global _lab
    _lab = lab


async def start_lab_career(fresh: bool = False) -> TrainerEngine:
    """Start (or resume) a career on the lab specimen."""
    lab = get_lab()
    state = await lab.start_career(fresh=fresh)
    return _reset_engine(state)


def _reset_engine(state: GameState | None = None) -> TrainerEngine:
    global _engine
    if state is None:
        state = GameState(dialogue=DEFAULT_INITIAL_DIALOGUE)
    _engine = TrainerEngine(initial_state=state)
    return _engine


# ---------------------------------------------------------------------------
# Request / response helpers
# ---------------------------------------------------------------------------

class DialogueRequest(BaseModel):
    event: str


class DialogueResponse(BaseModel):
    dialogue: str
    pose: str
    interactions_in_cycle: int = 0
    interactions_required: int = 10
    race_unlocked: bool = False


class ScanRequest(BaseModel):
    target_path: str = "."


def resolve_repo_path(target_path: str) -> str:
    """Resolve a repo path given relative to the cwd, the backend or the project root."""
    target_path = os.path.expanduser(target_path)
    for base in ("", str(BACKEND_DIR), str(PROJECT_ROOT)):
        candidate = os.path.join(base, target_path) if base else target_path
        if os.path.exists(candidate):
            return candidate
    return "."


def scan_into_engine(target_path: str) -> TrainerEngine:
    """Scan a repository and start a fresh engine seeded with its scores and smells."""
    target_path = resolve_repo_path(target_path)
    scores, smells = scan_repo_full(target_path)
    if _lab is not None:
        _lab.mode = "repo"
        _lab.experiment = None
        _lab.review = None
    new_state = GameState(
        repo_name=os.path.basename(os.path.abspath(target_path)) or "repo",
        attributes=scores,
        dialogue=DEFAULT_INITIAL_DIALOGUE,
    )
    engine = _reset_engine(new_state)
    engine.load_scan(smells, target_path)
    return engine


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/state", response_model=GameState)
async def get_state() -> GameState:
    """Return the current in-memory game state."""
    return _get_engine().state


@router.post("/scan", response_model=GameState)
async def scan(body: ScanRequest = Body(default=ScanRequest())) -> GameState:
    """Scan a repository path, set initial attributes and smells, and return new GameState."""
    return scan_into_engine(body.target_path).state


@router.post("/train", response_model=TrainResult)
async def train(req: TrainRequest) -> TrainResult:
    """Execute one training action, perform live DuckDuckGo MCP research, and return the result."""
    engine = _get_engine()
    result = engine.train(req.attribute)

    # 1. Real-time DuckDuckGo MCP Research
    mcp_insight = await McpResearchService.research_attribute(
        attribute=req.attribute,
        custom_topic=req.custom_knowledge,
    )

    # 2. Persist to Dr. Agnes's memory store & state
    memory_store.add_learned_insight(
        attribute=req.attribute,
        query=req.custom_knowledge or req.attribute.value,
        insight=mcp_insight,
    )
    recent_insights = [item["insight"] for item in memory_store.get_recent_insights(10)]
    engine.state = engine.state.model_copy(update={"learned_insights": recent_insights})
    updated_state = engine.state

    # 3. Enrich commentary prompt with both canonical curriculum and fresh web research
    rag_context = KnowledgeService.enrich_training_context(req.attribute)
    custom_part = f" User requested focus: '{req.custom_knowledge}'." if req.custom_knowledge else ""
    mcp_part = f" Latest DuckDuckGo Web Research Insight: '{mcp_insight}'." if mcp_insight else ""

    live_commentary = await _gateway.generate_dialogue(
        game_state=updated_state,
        event_description=(
            f"Training {req.attribute.value}: "
            f"{'success' if result.success else 'failure'}, "
            f"stat_gained={result.stat_gained}. "
            f"Studied Architecture Knowledge: {rag_context}.{mcp_part}{custom_part}"
        ),
    )

    # Return result with live commentary, updated state, and MCP insight
    return result.model_copy(update={
        "tachyon_commentary": live_commentary,
        "mcp_insight": mcp_insight,
        "updated_state": updated_state,
    })


@router.post("/rest", response_model=RestResult)
async def rest() -> RestResult:
    """Execute a rest action and return the result."""
    return _get_engine().rest()


@router.post("/race/simulate", response_model=list[RaceTick])
async def race_simulate() -> list[RaceTick]:
    """Run a full 100-tick race simulation and return all ticks."""
    attrs = _get_engine().state.attributes
    simulator = RaceSimulator(player_attributes=attrs)
    return simulator.run_simulation()


@router.get("/race/stream")
async def race_stream() -> StreamingResponse:
    """Stream each RaceTick as a Server-Sent Event with a 50 ms delay per tick."""
    attrs = _get_engine().state.attributes

    async def _event_generator() -> AsyncIterator[str]:
        simulator = RaceSimulator(player_attributes=attrs)
        async for tick in simulator.stream_simulation():
            data = tick.model_dump_json()
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.05)
        # Signal stream end
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _determine_pose(text: str, state: GameState) -> AvatarPose:
    """Infer the most expressive character pose from text and current game state."""
    if state.energy < 25:
        return AvatarPose.tired
    lower = text.lower()
    if any(k in lower for k in ["training failure", "disaster", "catastrophe", "syntax error", "exception", "broken build", "panic", "production incident", "unhandled"]):
        return AvatarPose.shocked
    if any(k in lower for k in ["fascinat", "ponder", "calculat", "hypothes", "analyz", "curious", "query", "inquir", "consider", "let us examine"]):
        return AvatarPose.thinking
    if any(k in lower for k in ["strict", "enterprise", "warn", "prescrib", "disciplin", "refactor", "crucial", "must", "fundament", "rule", "governance"]):
        return AvatarPose.serious
    if any(k in lower for k in ["exquisite", "magnificent", "splendid", "victory", "kukuku", "hehehe", "transcendental", "delight", "eureka", "brilliant"]):
        return AvatarPose.flow if state.mood == MoodState.GREAT else AvatarPose.happy
    if state.mood in [MoodState.GOOD, MoodState.GREAT]:
        return AvatarPose.happy
    return AvatarPose.thinking


@router.post("/dialogue", response_model=DialogueResponse)
async def dialogue(body: DialogueRequest) -> DialogueResponse:
    """Generate a live Tachyon dialogue response with dynamic expressive pose and update qualification cycle."""
    engine = _get_engine()
    text = await _gateway.generate_dialogue(
        game_state=engine.state,
        event_description=body.event,
    )
    # Store turn in memory for race quiz personalization
    memory_store.add_chat_turn(user_message=body.event, agnes_reply=text)

    # Increment qualification interaction count
    engine.record_chat_interaction()

    pose = _determine_pose(text, engine.state)
    engine.state = engine.state.model_copy(update={"current_pose": pose, "dialogue": text})
    return DialogueResponse(
        dialogue=text,
        pose=pose.value,
        interactions_in_cycle=engine.state.interactions_in_cycle,
        interactions_required=engine.state.interactions_required,
        race_unlocked=engine.state.race_unlocked,
    )


class AudioSynthesizeRequest(BaseModel):
    text: str
    voice: str = "jf_nezumi"
    speed: float = 1.04


@router.post("/audio/synthesize")
async def synthesize_audio(req: AudioSynthesizeRequest) -> Response:
    """Synthesize text into speech using Kokoro-82M via Featherless."""
    audio_bytes = await _tts.synthesize(text=req.text, voice=req.voice, speed=req.speed)
    if not audio_bytes:
        return Response(status_code=204)
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.get("/training/curriculum/{attribute}")
async def get_curriculum(attribute: str) -> dict:
    """Return the training curriculum card and cutscene cue for an attribute."""
    try:
        attr_enum = AttributeType(attribute.lower())
    except ValueError:
        attr_enum = AttributeType.WISDOM
    return KnowledgeService.get_curriculum(attr_enum)


@router.get("/race/quiz", response_model=list[QuizQuestion])
async def get_race_quiz() -> list[QuizQuestion]:
    """Generate or retrieve a personalized 3-question architecture exam for the Grand Derby."""
    return await QuizService.generate_personalized_quiz(store=memory_store, gateway=_gateway)


@router.post("/race/evaluate-quiz", response_model=QuizEvaluationResponse)
async def evaluate_race_quiz(req: QuizEvaluationRequest) -> QuizEvaluationResponse:
    """Evaluate player's architectural choice at a race checkpoint and calculate speed multiplier."""
    return QuizService.evaluate_answer(question_id=req.question_id, selected_index=req.selected_index)


@router.post("/race/complete", response_model=GameState)
async def complete_race(req: RaceCompleteRequest = Body(default=RaceCompleteRequest())) -> GameState:
    """Complete the Grand Derby and reset the 10-interaction cycle."""
    engine = _get_engine()
    return engine.reset_cycle()

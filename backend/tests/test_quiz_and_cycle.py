"""Unit tests for DuckDuckGo MCP Research, Agnes Memory Store, Architecture Quiz, and 10-Interaction Cycle."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.schemas import AttributeType, GameState
from app.services.knowledge_service import AgnesMemoryStore
from app.services.mcp_research_service import McpResearchService
from app.services.quiz_service import QuizService
from app.services.trainer_service import TrainerEngine


@pytest.fixture
def clean_memory_store():
    store = AgnesMemoryStore()
    return store


@pytest.fixture
def trainer_engine():
    return TrainerEngine()


def test_memory_store_recording(clean_memory_store):
    store = clean_memory_store
    store.add_learned_insight(
        attribute=AttributeType.SPEED,
        query="asyncio event loop 2026",
        insight="uvloop maximizes cooperative coroutine throughput.",
    )
    store.add_chat_turn(
        user_message="How does Pix DICT work?",
        agnes_reply="DICT is the synaptic directory resolving keys in milliseconds.",
    )

    assert len(store.learned_insights) == 1
    assert len(store.chat_turns) == 1

    summary = store.get_memory_summary()
    assert "DUCKDUCKGO MCP RESEARCH" in summary
    assert "uvloop" in summary
    assert "Pix DICT" in summary


@pytest.mark.asyncio
async def test_mcp_research_fallback():
    # Calling research_attribute should return high quality technical literature even when offline
    insight = await McpResearchService.research_attribute(AttributeType.WISDOM)
    assert isinstance(insight, str)
    assert len(insight) > 20
    assert any(term in insight.lower() for term in ["ddd", "architecture", "domain", "aggregate"])


@pytest.mark.asyncio
async def test_quiz_generation_and_evaluation():
    store = AgnesMemoryStore()
    store.add_chat_turn("Can you explain Brazilian Pix architecture?", "DICT resolves keys before SPI settlement.")

    quiz = await QuizService.generate_personalized_quiz(store=store)
    assert len(quiz) >= 2
    for q in quiz:
        assert q.question
        assert len(q.options) >= 2
        assert q.id

    # Test evaluation
    q1 = quiz[0]
    eval_resp = QuizService.evaluate_answer(question_id=q1.id, selected_index=1)
    assert isinstance(eval_resp.correct, bool)
    assert eval_resp.explanation
    assert isinstance(eval_resp.speed_delta, float)


def test_trainer_10_interaction_cycle(trainer_engine):
    engine = trainer_engine
    assert engine.state.interactions_in_cycle == 0
    assert not engine.state.race_unlocked

    # 9 chat interactions
    for _ in range(9):
        engine.record_chat_interaction()
    assert engine.state.interactions_in_cycle == 9
    assert not engine.state.race_unlocked

    # 10th interaction unlocks the Grand Derby
    engine.record_chat_interaction()
    assert engine.state.interactions_in_cycle == 10
    assert engine.state.race_unlocked

    # Complete race resets the cycle
    engine.reset_cycle()
    assert engine.state.interactions_in_cycle == 0
    assert not engine.state.race_unlocked


@pytest.mark.asyncio
async def test_api_quiz_and_cycle_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Check quiz endpoint
        quiz_resp = await ac.get("/api/race/quiz")
        assert quiz_resp.status_code == 200
        quiz_data = quiz_resp.json()
        assert len(quiz_data) >= 2

        # 2. Evaluate answer
        first_q = quiz_data[0]
        eval_resp = await ac.post(
            "/api/race/evaluate-quiz",
            json={"question_id": first_q["id"], "selected_index": 1},
        )
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()
        assert "correct" in eval_data
        assert "speed_delta" in eval_data

        # 3. Test dialogue increments cycle
        state_before = (await ac.get("/api/state")).json()
        count_before = state_before.get("interactions_in_cycle", 0)

        dial_resp = await ac.post("/api/dialogue", json={"event": "Audit domain aggregate boundaries"})
        assert dial_resp.status_code == 200
        dial_data = dial_resp.json()
        assert dial_data["interactions_in_cycle"] == count_before + 1

        # 4. Complete race resets cycle
        complete_resp = await ac.post("/api/race/complete", json={"place": 1, "points_awarded": 300})
        assert complete_resp.status_code == 200
        reset_state = complete_resp.json()
        assert reset_state["interactions_in_cycle"] == 0
        assert not reset_state["race_unlocked"]

"""Unit tests for backend/app/services/trainer_service.py — Mission 03."""
from __future__ import annotations

import math
from unittest.mock import patch

import pytest

from app.models.schemas import (
    AttributeType,
    AvatarPose,
    GameState,
    MoodState,
    RestResult,
    TrainResult,
)
from app.services.trainer_service import TrainerEngine, _mood_down, _mood_up


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _engine(energy: int = 100, mood: MoodState = MoodState.NORMAL, turn: int = 1) -> TrainerEngine:
    state = GameState(energy=energy, mood=mood, turn=turn)
    return TrainerEngine(initial_state=state)


# ===========================================================================
# calculate_failure_rate — energy thresholds
# ===========================================================================

class TestFailureRate:
    @pytest.mark.parametrize("energy,expected", [
        (100, 0.00),
        (80,  0.00),
        (79,  0.05),
        (60,  0.05),
        (59,  0.18),
        (40,  0.18),
        (39,  0.45),
        (20,  0.45),
        (19,  0.75),
        (0,   0.75),
    ])
    def test_failure_rate_thresholds(self, energy: int, expected: float):
        engine = _engine(energy=energy)
        assert engine.calculate_failure_rate() == pytest.approx(expected)

    def test_failure_rate_reflects_current_state(self):
        engine = _engine(energy=100)
        assert engine.calculate_failure_rate() == 0.0
        engine.state.energy = 10
        assert engine.calculate_failure_rate() == 0.75


# ===========================================================================
# _mood_down / _mood_up helpers
# ===========================================================================

class TestMoodTransitions:
    def test_mood_down_from_good(self):
        assert _mood_down(MoodState.GOOD) == MoodState.NORMAL

    def test_mood_down_floors_at_terrible(self):
        assert _mood_down(MoodState.TERRIBLE) == MoodState.TERRIBLE

    def test_mood_up_from_normal(self):
        assert _mood_up(MoodState.NORMAL) == MoodState.GOOD

    def test_mood_up_caps_at_great(self):
        assert _mood_up(MoodState.GREAT) == MoodState.GREAT

    def test_mood_down_full_chain(self):
        mood = MoodState.GREAT
        expected = [MoodState.GOOD, MoodState.NORMAL, MoodState.POOR, MoodState.TERRIBLE, MoodState.TERRIBLE]
        for exp in expected:
            mood = _mood_down(mood)
            assert mood == exp


# ===========================================================================
# train — success path
# ===========================================================================

class TestTrainSuccess:
    """Force random.random() > failure_rate so train always succeeds."""

    def _train_success(self, energy: int = 100, mood: MoodState = MoodState.NORMAL) -> TrainResult:
        engine = _engine(energy=energy, mood=mood)
        _success_commentary = "Ufufu… the specimen shows remarkable adaptation."
        with patch("app.services.trainer_service.random.random", return_value=1.0), \
             patch("app.services.trainer_service.random.randint", return_value=30), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.happy, _success_commentary]):
            return engine.train(AttributeType.SPEED)

    def test_success_flag(self):
        result = self._train_success()
        assert result.success is True

    def test_stat_gained_positive(self):
        result = self._train_success()
        assert result.stat_gained > 0

    def test_energy_drops_by_20(self):
        result = self._train_success(energy=100)
        assert result.updated_state.energy == 80
        assert result.energy_spent == 20

    def test_turn_increments(self):
        engine = _engine(energy=100)
        initial_turn = engine.state.turn
        with patch("app.services.trainer_service.random.random", return_value=1.0), \
             patch("app.services.trainer_service.random.randint", return_value=30), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.happy, "commentary"]):
            result = engine.train(AttributeType.SPEED)
        assert result.updated_state.turn == initial_turn + 1

    def test_attribute_score_increases(self):
        engine = _engine(energy=100)
        before = engine.state.attributes.speed
        with patch("app.services.trainer_service.random.random", return_value=1.0), \
             patch("app.services.trainer_service.random.randint", return_value=30), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.happy, "commentary"]):
            result = engine.train(AttributeType.SPEED)
        assert result.updated_state.attributes.speed > before

    def test_pose_is_happy_or_serious(self):
        result = self._train_success()
        assert result.pose in (AvatarPose.happy, AvatarPose.serious)

    def test_commentary_non_empty(self):
        result = self._train_success()
        assert result.tachyon_commentary

    # ---- Mood multipliers ----
    @pytest.mark.parametrize("mood,base,expected_min,expected_max", [
        (MoodState.GREAT,   30, 36, 36),  # round(30 * 1.20) = 36
        (MoodState.GOOD,    30, 33, 33),  # round(30 * 1.10) = 33
        (MoodState.NORMAL,  30, 30, 30),  # round(30 * 1.00) = 30
        (MoodState.POOR,    30, 27, 27),  # round(30 * 0.90) = 27
        (MoodState.TERRIBLE,30, 24, 24),  # round(30 * 0.80) = 24
    ])
    def test_mood_multiplier_alters_stat_gain(self, mood, base, expected_min, expected_max):
        engine = _engine(energy=100, mood=mood)
        with patch("app.services.trainer_service.random.random", return_value=1.0), \
             patch("app.services.trainer_service.random.randint", return_value=base), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.happy, "commentary"]):
            result = engine.train(AttributeType.STAMINA)
        assert expected_min <= result.stat_gained <= expected_max

    def test_success_mood_unchanged(self):
        engine = _engine(energy=100, mood=MoodState.GOOD)
        with patch("app.services.trainer_service.random.random", return_value=1.0), \
             patch("app.services.trainer_service.random.randint", return_value=30), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.happy, "commentary"]):
            result = engine.train(AttributeType.SPEED)
        assert result.updated_state.mood == MoodState.GOOD


# ===========================================================================
# train — failure path
# ===========================================================================

class TestTrainFailure:
    """Force random.random() < failure_rate so train always fails."""

    def _train_fail(self, energy: int = 10, mood: MoodState = MoodState.NORMAL) -> TrainResult:
        engine = _engine(energy=energy, mood=mood)
        _fail_commentary = "Kukuku… a catastrophic metabolic failure!"
        with patch("app.services.trainer_service.random.random", return_value=0.0), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.shocked, _fail_commentary]):
            return engine.train(AttributeType.POWER)

    def test_failure_flag(self):
        result = self._train_fail()
        assert result.success is False

    def test_stat_gained_is_zero(self):
        result = self._train_fail()
        assert result.stat_gained == 0

    def test_energy_drops_by_15(self):
        result = self._train_fail(energy=30)
        assert result.updated_state.energy == 15
        assert result.energy_spent == 15

    def test_mood_drops_one_rank(self):
        result = self._train_fail(mood=MoodState.GOOD)
        assert result.updated_state.mood == MoodState.NORMAL

    def test_mood_does_not_drop_below_terrible(self):
        result = self._train_fail(mood=MoodState.TERRIBLE)
        assert result.updated_state.mood == MoodState.TERRIBLE

    def test_pose_is_shocked_or_tired(self):
        result = self._train_fail()
        assert result.pose in (AvatarPose.shocked, AvatarPose.tired)

    def test_commentary_non_empty(self):
        result = self._train_fail()
        assert result.tachyon_commentary

    def test_turn_increments_on_failure(self):
        engine = _engine(energy=10)
        initial_turn = engine.state.turn
        with patch("app.services.trainer_service.random.random", return_value=0.0), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.tired, "commentary"]):
            result = engine.train(AttributeType.GUTS)
        assert result.updated_state.turn == initial_turn + 1

    def test_energy_clamped_at_zero(self):
        """Failing with very low energy must not go below 0."""
        result = self._train_fail(energy=5)
        assert result.updated_state.energy >= 0


# ===========================================================================
# rest
# ===========================================================================

class TestRest:
    _REST_COMMENTARY = "Rest is not laziness."

    def test_energy_recovers_45(self):
        engine = _engine(energy=50)
        with patch("app.services.trainer_service.random.random", return_value=0.5), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.idle, self._REST_COMMENTARY]):
            result = engine.rest()
        assert result.energy_recovered == 45
        assert result.updated_state.energy == 95

    def test_energy_clamped_at_100(self):
        """Energy must never exceed 100 after rest."""
        engine = _engine(energy=70)
        with patch("app.services.trainer_service.random.random", return_value=0.5), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.idle, self._REST_COMMENTARY]):
            result = engine.rest()
        assert result.updated_state.energy == 100
        assert result.energy_recovered == 30

    def test_full_energy_recovers_zero(self):
        """Resting at full energy recovers nothing."""
        engine = _engine(energy=100)
        with patch("app.services.trainer_service.random.random", return_value=0.5), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.idle, self._REST_COMMENTARY]):
            result = engine.rest()
        assert result.energy_recovered == 0
        assert result.updated_state.energy == 100

    def test_mood_improves_when_lucky(self):
        engine = _engine(energy=50, mood=MoodState.NORMAL)
        with patch("app.services.trainer_service.random.random", return_value=0.1), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.idle, self._REST_COMMENTARY]):
            result = engine.rest()
        assert result.new_mood == MoodState.GOOD

    def test_mood_unchanged_when_unlucky(self):
        engine = _engine(energy=50, mood=MoodState.NORMAL)
        with patch("app.services.trainer_service.random.random", return_value=0.9), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.idle, self._REST_COMMENTARY]):
            result = engine.rest()
        assert result.new_mood == MoodState.NORMAL

    def test_mood_caps_at_great(self):
        engine = _engine(energy=50, mood=MoodState.GREAT)
        with patch("app.services.trainer_service.random.random", return_value=0.1), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.idle, self._REST_COMMENTARY]):
            result = engine.rest()
        assert result.new_mood == MoodState.GREAT

    def test_turn_increments_on_rest(self):
        engine = _engine(energy=50)
        initial_turn = engine.state.turn
        with patch("app.services.trainer_service.random.random", return_value=0.5), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.idle, self._REST_COMMENTARY]):
            result = engine.rest()
        assert result.updated_state.turn == initial_turn + 1

    def test_pose_is_idle_or_thinking(self):
        engine = _engine(energy=50)
        with patch("app.services.trainer_service.random.random", return_value=0.5), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.thinking, self._REST_COMMENTARY]):
            result = engine.rest()
        assert result.updated_state.current_pose in (AvatarPose.idle, AvatarPose.thinking)

    def test_rest_returns_rest_result(self):
        engine = _engine(energy=50)
        with patch("app.services.trainer_service.random.random", return_value=0.5), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.idle, self._REST_COMMENTARY]):
            result = engine.rest()
        assert isinstance(result, RestResult)


# ===========================================================================
# Game over trigger
# ===========================================================================

class TestGameOver:
    def test_game_over_when_turn_exceeds_max(self):
        """Training on the last turn must set is_game_over = True."""
        # Set turn = max_turns so that after +1 it exceeds max
        state = GameState(energy=100, turn=12, max_turns=12)
        engine = TrainerEngine(initial_state=state)
        with patch("app.services.trainer_service.random.random", return_value=1.0), \
             patch("app.services.trainer_service.random.randint", return_value=30), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.happy, "commentary"]):
            result = engine.train(AttributeType.SPEED)
        assert result.updated_state.is_game_over is True
        assert result.updated_state.turn == 13

    def test_not_game_over_before_max(self):
        state = GameState(energy=100, turn=1, max_turns=12)
        engine = TrainerEngine(initial_state=state)
        with patch("app.services.trainer_service.random.random", return_value=1.0), \
             patch("app.services.trainer_service.random.randint", return_value=30), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.happy, "commentary"]):
            result = engine.train(AttributeType.SPEED)
        assert result.updated_state.is_game_over is False

    def test_game_over_via_rest(self):
        state = GameState(energy=50, turn=12, max_turns=12)
        engine = TrainerEngine(initial_state=state)
        with patch("app.services.trainer_service.random.random", return_value=0.5), \
             patch("app.services.trainer_service.random.choice",
                   side_effect=[AvatarPose.idle, "rest commentary"]):
            result = engine.rest()
        assert result.updated_state.is_game_over is True


# ===========================================================================
# generate_bob_prompt
# ===========================================================================

class TestGenerateBobPrompt:
    def _make_prompt(self, attribute: AttributeType = AttributeType.SPEED) -> str:
        engine = _engine()
        return engine.generate_bob_prompt(
            attribute=attribute,
            target_file="app/services/worker.py",
            smell_description="`time.sleep(5)` called inside `async def fetch()`.",
            code_snippet="async def fetch():\n    time.sleep(5)\n    return requests.get(url)",
        )

    def test_prompt_contains_attribute(self):
        prompt = self._make_prompt(AttributeType.SPEED)
        assert "SPEED" in prompt

    def test_prompt_contains_file_path(self):
        prompt = self._make_prompt()
        assert "app/services/worker.py" in prompt

    def test_prompt_contains_smell_description(self):
        prompt = self._make_prompt()
        assert "time.sleep" in prompt

    def test_prompt_contains_code_snippet(self):
        prompt = self._make_prompt()
        assert "async def fetch" in prompt

    def test_prompt_under_800_tokens(self):
        """Rough token estimate: 1 token ≈ 4 chars."""
        prompt = self._make_prompt()
        estimated_tokens = len(prompt) / 4
        assert estimated_tokens < 800, f"Prompt too long: ~{estimated_tokens:.0f} tokens"

    def test_prompt_contains_ibm_bob_instruction(self):
        prompt = self._make_prompt()
        # Must instruct Bob to make a minimal, surgical change
        assert "IBM Bob" in prompt or "apply_diff" in prompt or "minimal" in prompt.lower()

    @pytest.mark.parametrize("attribute", list(AttributeType))
    def test_all_attributes_produce_non_empty_prompt(self, attribute: AttributeType):
        engine = _engine()
        prompt = engine.generate_bob_prompt(
            attribute=attribute,
            target_file="main.py",
            smell_description="Some smell.",
            code_snippet="def foo(): pass",
        )
        assert len(prompt) > 50

    def test_state_not_mutated_by_prompt_generation(self):
        engine = _engine(energy=75, mood=MoodState.GOOD, turn=3)
        before_turn = engine.state.turn
        before_energy = engine.state.energy
        engine.generate_bob_prompt(
            attribute=AttributeType.WISDOM,
            target_file="x.py",
            smell_description="No return type.",
            code_snippet="def foo(): pass",
        )
        assert engine.state.turn == before_turn
        assert engine.state.energy == before_energy


# ===========================================================================
# Initial state isolation
# ===========================================================================

class TestInitialState:
    def test_default_state_is_fresh_game_state(self):
        engine = TrainerEngine()
        assert engine.state == GameState()

    def test_passed_state_is_deep_copied(self):
        original = GameState(energy=60)
        engine = TrainerEngine(initial_state=original)
        engine.state.energy = 10
        # Original must be untouched
        assert original.energy == 60

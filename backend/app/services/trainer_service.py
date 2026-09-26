"""Trainer & Motivation State Machine — core training game loop."""
from __future__ import annotations

import copy
import random

from app.models.schemas import (
    AttributeScores,
    AttributeType,
    AvatarPose,
    GameState,
    MoodState,
    RestResult,
    TrainResult,
)

# ---------------------------------------------------------------------------
# Mood ordering — used to step up/down one rank
# ---------------------------------------------------------------------------
_MOOD_ORDER: list[MoodState] = [
    MoodState.TERRIBLE,
    MoodState.POOR,
    MoodState.NORMAL,
    MoodState.GOOD,
    MoodState.GREAT,
]

# Multiplier table: mood → float factor applied on top of base gain
_MOOD_MULTIPLIER: dict[MoodState, float] = {
    MoodState.GREAT: 1.20,
    MoodState.GOOD: 1.10,
    MoodState.NORMAL: 1.00,
    MoodState.POOR: 0.90,
    MoodState.TERRIBLE: 0.80,
}

# Tachyon commentaries (success)
_TACHYON_SUCCESS: list[str] = [
    "Ufufu… the specimen shows remarkable adaptation. A fine pharmacological side-effect of clean code!",
    "As expected — a controlled experiment yields controlled gains. Your refactoring compound is working.",
    "The metabolic rate of your codebase has increased. How delightfully scientific.",
    "A splendid result, Morumotto-kun. Even my most volatile elixirs rarely improve the subject this quickly.",
    "Progress within predicted parameters. I shall note this in my laboratory journal with great satisfaction.",
    "Kukuku… the architectural transformation proceeds exactly as hypothesised. Fascinating.",
]

# Tachyon commentaries (failure)
_TACHYON_FAILURE: list[str] = [
    "Kukuku… a catastrophic metabolic failure! You pushed the specimen with low energy, Morumotto-kun!",
    "Kukuku… the experiment collapsed — insufficient energy reserves corrupted the refactoring compound.",
    "How entertaining. Low energy produces low results. This is basic biochemistry, Morumotto-kun.",
    "A failed trial. Even science has its setbacks — though yours was entirely preventable.",
    "Kukuku… did you really think fatigued code could absorb the training dose? Rest first, then train.",
]

# Tachyon commentaries (rest)
_TACHYON_REST: list[str] = [
    "Rest is not laziness — it is the incubation period between experimental cycles. Even I sleep occasionally.",
    "Recovery time. I shall use this interval to formulate a new architectural drug. Do not disturb my notes.",
    "Fascinating — the specimen recuperates. Energy replenishment is as important as the training stimulus itself.",
    "Ufufu… a strategic withdrawal. Let the codebase metabolise the previous session before the next dosage.",
    "Even the most potent elixir requires time to bind. Rest, and tomorrow we refactor with renewed vigour.",
]


def _mood_down(mood: MoodState) -> MoodState:
    """Drop mood by one rank (floors at TERRIBLE)."""
    idx = _MOOD_ORDER.index(mood)
    return _MOOD_ORDER[max(0, idx - 1)]


def _mood_up(mood: MoodState) -> MoodState:
    """Raise mood by one rank (caps at GREAT)."""
    idx = _MOOD_ORDER.index(mood)
    return _MOOD_ORDER[min(len(_MOOD_ORDER) - 1, idx + 1)]


# ---------------------------------------------------------------------------
# TrainerEngine
# ---------------------------------------------------------------------------

class TrainerEngine:
    """Manages the training loop for a single play-through."""

    def __init__(self, initial_state: GameState | None = None) -> None:
        self.state: GameState = (
            copy.deepcopy(initial_state) if initial_state is not None else GameState()
        )

    # ------------------------------------------------------------------ #
    # Failure rate
    # ------------------------------------------------------------------ #

    def calculate_failure_rate(self) -> float:
        """Return the probability [0.0, 0.75] of a training failure based on energy."""
        energy = self.state.energy
        if energy >= 80:
            return 0.0
        if energy >= 60:
            return 0.05
        if energy >= 40:
            return 0.18
        if energy >= 20:
            return 0.45
        return 0.75

    # ------------------------------------------------------------------ #
    # Train
    # ------------------------------------------------------------------ #

    def train(self, attribute: AttributeType) -> TrainResult:
        """Execute one training action and return the result."""
        state = self.state
        failure_rate = self.calculate_failure_rate()
        failed = random.random() < failure_rate

        if not failed:
            # --- Success path ---
            base_gain = random.randint(25, 35)
            multiplier = _MOOD_MULTIPLIER[state.mood]
            stat_gained = max(1, round(base_gain * multiplier))
            energy_spent = 20
            pose = random.choice([AvatarPose.happy, AvatarPose.serious])
            commentary = random.choice(_TACHYON_SUCCESS)

            # Apply stat gain
            new_attrs = state.attributes.model_copy(
                update={attribute.value: getattr(state.attributes, attribute.value) + stat_gained}
            )
            new_energy = max(0, state.energy - energy_spent)
            new_mood = state.mood  # mood unchanged on success
        else:
            # --- Failure path ---
            stat_gained = 0
            energy_spent = 15
            pose = random.choice([AvatarPose.shocked, AvatarPose.tired])
            commentary = random.choice(_TACHYON_FAILURE)

            new_attrs = state.attributes
            new_energy = max(0, state.energy - energy_spent)
            new_mood = _mood_down(state.mood)

        # Advance turn; check game over
        new_turn = state.turn + 1
        is_game_over = new_turn > state.max_turns
        new_interactions = state.interactions_in_cycle + 1
        race_unlocked = new_interactions >= state.interactions_required

        updated = state.model_copy(update={
            "attributes": new_attrs,
            "energy": new_energy,
            "mood": new_mood,
            "turn": new_turn,
            "current_pose": pose,
            "dialogue": commentary,
            "is_game_over": is_game_over,
            "interactions_in_cycle": new_interactions,
            "race_unlocked": race_unlocked,
        })

        # Persist state
        self.state = updated

        return TrainResult(
            success=not failed,
            attribute=attribute,
            stat_gained=stat_gained,
            energy_spent=energy_spent,
            failure_rate=failure_rate,
            tachyon_commentary=commentary,
            pose=pose,
            updated_state=updated,
        )

    # ------------------------------------------------------------------ #
    # Rest
    # ------------------------------------------------------------------ #

    def rest(self) -> RestResult:
        """Recover energy and possibly improve mood."""
        state = self.state
        energy_recovered = min(45, 100 - state.energy)
        new_energy = state.energy + energy_recovered

        # 40% chance to improve mood by one stage
        new_mood = _mood_up(state.mood) if random.random() < 0.40 else state.mood

        # Advance turn; check game over
        new_turn = state.turn + 1
        is_game_over = new_turn > state.max_turns

        pose = random.choice([AvatarPose.idle, AvatarPose.thinking])
        commentary = random.choice(_TACHYON_REST)

        updated = state.model_copy(update={
            "energy": new_energy,
            "mood": new_mood,
            "turn": new_turn,
            "current_pose": pose,
            "dialogue": commentary,
            "is_game_over": is_game_over,
        })

        self.state = updated

        return RestResult(
            energy_recovered=energy_recovered,
            new_mood=new_mood,
            tachyon_commentary=commentary,
            updated_state=updated,
        )

    # ------------------------------------------------------------------ #
    # Interaction Cycle & Qualification
    # ------------------------------------------------------------------ #

    def record_chat_interaction(self) -> GameState:
        """Increment interaction counter when user chats with Dr. Agnes, unlocking the Derby at 10."""
        new_interactions = self.state.interactions_in_cycle + 1
        race_unlocked = new_interactions >= self.state.interactions_required
        self.state = self.state.model_copy(update={
            "interactions_in_cycle": new_interactions,
            "race_unlocked": race_unlocked,
        })
        return self.state

    def reset_cycle(self) -> GameState:
        """Reset the 10-interaction qualification cycle after a completed Grand Derby."""
        self.state = self.state.model_copy(update={
            "interactions_in_cycle": 0,
            "race_unlocked": False,
        })
        return self.state

    # ------------------------------------------------------------------ #
    # Bob refactoring prompt
    # ------------------------------------------------------------------ #

    def generate_bob_prompt(
        self,
        attribute: AttributeType,
        target_file: str,
        smell_description: str,
        code_snippet: str,
    ) -> str:
        """Return a token-efficient Markdown prompt (< 800 tokens) for IBM Bob."""
        attribute_guide: dict[AttributeType, str] = {
            AttributeType.SPEED: (
                "Replace blocking calls with async equivalents "
                "(e.g. `asyncio.sleep`, `httpx.AsyncClient`). "
                "Reduce cyclomatic complexity to ≤ 10 branches per function."
            ),
            AttributeType.STAMINA: (
                "Wrap all resource acquisitions (`open`, DB cursors/connections) "
                "in `with` / `async with` context managers to eliminate leaks."
            ),
            AttributeType.POWER: (
                "Replace sequential per-item loops with concurrent or batch processing "
                "(`asyncio.gather`, `ThreadPoolExecutor`, or bulk API calls)."
            ),
            AttributeType.GUTS: (
                "Replace bare `except` / `except Exception: pass` with specific exception "
                "types and at minimum log the error. Add explicit `timeout=` to all HTTP calls."
            ),
            AttributeType.WISDOM: (
                "Add return type annotations to all public functions. "
                "Decompose functions longer than 80 lines into focused helpers."
            ),
        }

        prescription = attribute_guide[attribute]

        return f"""\
# 🔬 Dr. Tachyon's Refactoring Prescription

**Attribute targeted:** `{attribute.value.upper()}` \\
**File:** `{target_file}`

## Detected Smell
{smell_description}

## Code Under Analysis
```python
{code_snippet}
```

## Prescription
{prescription}

## Task for IBM Bob
Apply the **minimal surgical change** that resolves the smell above.
- Do **not** refactor unrelated code.
- Do **not** change public interfaces unless strictly necessary.
- Preserve existing tests; add a new test only if none covers the fixed path.
- Emit only the modified lines (use `apply_diff` or `search_and_replace`).

*— Agnes Tachyon, Chief Architect of Experimental Pharmacology*
"""

"""Trainer & Motivation State Machine — core training game loop."""
from __future__ import annotations

import copy
import os
import random
from typing import TYPE_CHECKING

from app.models.schemas import (
    AttributeScores,
    AttributeType,
    AvatarPose,
    CodeSmell,
    GameState,
    MoodState,
    RescanResult,
    RestResult,
    TrainResult,
)

if TYPE_CHECKING:
    from app.services.scanner_service import DetectedSmell

# Extra stat gain when a training session drills a real code smell
_SMELL_DRILL_BONUS = 8

# Rule severity (mirrors the scanner penalties) — worst smells are listed first
_RULE_SEVERITY: dict[str, int] = {
    "STAMINA-001": 50, "SPEED-001": 40, "STAMINA-002": 40, "WISDOM-002": 35,
    "SPEED-002": 30, "POWER-001": 30, "GUTS-001": 30, "GUTS-002": 25, "WISDOM-001": 20,
    # whole-program analyzer rules (app.lab.findings)
    "STAMINA-003": 55, "SPEED-003": 45, "STAMINA-004": 45, "WISDOM-003": 40, "POWER-002": 35, "WISDOM-004": 30,
}

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
        # Attributes = scanned base + accumulated training bonus, so a rescan
        # can refresh the base from real code without erasing training progress.
        self.base_attributes: AttributeScores = self.state.attributes.model_copy()
        self.training_bonus: dict[str, int] = {a.value: 0 for a in AttributeType}
        self.smells: list[CodeSmell] = []
        self._next_smell_id = 1
        self.repo_root: str = "."

    # ------------------------------------------------------------------ #
    # Code smells (real scanner findings)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _smell_key(detected: "DetectedSmell", repo_root: str) -> str:
        rel = os.path.relpath(detected.file_path, repo_root)
        return f"{detected.rule_id}|{rel}|{detected.description}"

    def _to_code_smell(self, detected: "DetectedSmell", repo_root: str, key: str) -> CodeSmell:
        smell = CodeSmell(
            id=self._next_smell_id,
            key=key,
            attribute=detected.attribute,
            rule_id=detected.rule_id,
            file_path=os.path.relpath(detected.file_path, repo_root),
            line_number=detected.line_number,
            description=detected.description,
            tachyon_critique=detected.tachyon_critique,
            suggested_fix=detected.suggested_fix,
            code_snippet=detected.code_snippet,
        )
        self._next_smell_id += 1
        return smell

    def load_scan(self, detected: list["DetectedSmell"], repo_root: str) -> None:
        """Replace the tracked smells with a fresh scan (numbered from 1)."""
        self.repo_root = repo_root
        self.smells = []
        self._next_smell_id = 1
        # Number worst-first so "smell number one" is the one that matters most.
        ranked = sorted(
            enumerate(detected),
            key=lambda p: (-_RULE_SEVERITY.get(p[1].rule_id, 0), p[0]),
        )
        for _, d in ranked:
            self.smells.append(self._to_code_smell(d, repo_root, self._smell_key(d, repo_root)))

    def open_smells(self, attribute: AttributeType | None = None) -> list[CodeSmell]:
        """Smells not yet drilled in training (worst first), optionally filtered by attribute."""
        found = [
            s for s in self.smells
            if not s.drilled and (attribute is None or s.attribute == attribute)
        ]
        return sorted(found, key=lambda s: (-_RULE_SEVERITY.get(s.rule_id, 0), s.id))

    def get_smell(self, smell_id: int) -> CodeSmell | None:
        return next((s for s in self.smells if s.id == smell_id), None)

    def rescan(
        self,
        scores: AttributeScores,
        detected: list["DetectedSmell"],
        repo_root: str,
    ) -> RescanResult:
        """Diff a new scan against tracked smells and refresh the scanned base.

        Smells whose key disappeared were really fixed in the code; they drop
        off the list. Surviving smells keep their id (and drilled flag) so the
        numbers the trainer has been hearing stay stable.
        """
        old_by_key = {s.key: s for s in self.smells}
        new_keys: list[str] = []
        kept: list[CodeSmell] = []
        new: list[CodeSmell] = []
        for d in detected:
            key = self._smell_key(d, repo_root)
            new_keys.append(key)
            if key in old_by_key:
                prev = old_by_key[key]
                kept.append(prev.model_copy(update={
                    "line_number": d.line_number,
                    "code_snippet": d.code_snippet,
                }))
            else:
                smell = self._to_code_smell(d, repo_root, key)
                kept.append(smell)
                new.append(smell)
        fixed = [s for k, s in old_by_key.items() if k not in set(new_keys)]
        self.smells = kept

        deltas = {
            a.value: getattr(scores, a.value) - getattr(self.base_attributes, a.value)
            for a in AttributeType
        }
        self.base_attributes = scores.model_copy()
        new_attrs = AttributeScores(**{
            a.value: getattr(scores, a.value) + self.training_bonus[a.value]
            for a in AttributeType
        })
        pose = AvatarPose.happy if fixed and not new else (
            AvatarPose.shocked if new and not fixed else AvatarPose.thinking
        )
        self.state = self.state.model_copy(update={
            "attributes": new_attrs,
            "current_pose": pose,
        })
        return RescanResult(
            fixed=fixed,
            new=new,
            remaining=len(self.open_smells()),
            attribute_deltas=deltas,
            updated_state=self.state,
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

    def train(self, attribute: AttributeType, smell_id: int | None = None) -> TrainResult:
        """Execute one training action and return the result.

        Training drills a real code smell when one is available: the given
        ``smell_id`` (whose attribute wins), otherwise the first open smell of
        ``attribute``. A successful drill grants a bonus and marks it drilled.
        """
        smell = self.get_smell(smell_id) if smell_id is not None else None
        if smell is not None:
            attribute = smell.attribute
        else:
            candidates = self.open_smells(attribute)
            smell = candidates[0] if candidates else None

        state = self.state
        failure_rate = self.calculate_failure_rate()
        failed = random.random() < failure_rate

        if not failed:
            # --- Success path ---
            base_gain = random.randint(25, 35)
            multiplier = _MOOD_MULTIPLIER[state.mood]
            stat_gained = max(1, round(base_gain * multiplier))
            if smell is not None and not smell.drilled:
                stat_gained += _SMELL_DRILL_BONUS
                smell = smell.model_copy(update={"drilled": True})
                self.smells = [smell if s.id == smell.id else s for s in self.smells]
            self.training_bonus[attribute.value] += stat_gained
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
            smell=smell,
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

"""The trainer's persistent profile: what Agnes remembers between careers.

* **Mastery** per concept (0-100) plus Leitner-box spaced repetition: a
  concept you got right comes back for review after 1, 2, 4, 8, then 16 lab
  days; a miss sends it back to box 1.
* **Bond** with Agnes, which unlocks titles and Eureka experiments.
* **Calibration**: how often your *certain* predictions were right.
* **Hall of Fame**: every finished career, with its stats and placement.
* **Sparks**: inherited per mastered concept, they become Derby skills.
* **Journal**: lore entries unlocked by finishing chapters.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone

from pydantic import BaseModel, Field

LEITNER_DAYS = [1, 2, 4, 8, 16]

BOND_TITLES = [
    (0, "Test Subject"),
    (30, "Lab Assistant"),
    (60, "Research Partner"),
    (90, "Co-author"),
]


class ConceptRecord(BaseModel):
    mastery: int = 0
    box: int = 0                 # 0 = never studied
    due_day: int = 0
    experiments: int = 0
    reviews_right: int = 0
    reviews_wrong: int = 0
    best_score: int = 0


class HallEntry(BaseModel):
    career: int
    finished_at: str
    trainee: str
    place: int
    checkpoint_score: int
    attributes: dict[str, int]
    chapters_cleared: list[int]
    sparks: dict[str, int] = Field(default_factory=dict)


class Profile(BaseModel):
    version: int = 1
    lab_day: int = 1
    career: int = 1
    bond: int = 0
    concepts: dict[str, ConceptRecord] = Field(default_factory=dict)
    certain_right: int = 0
    certain_wrong: int = 0
    predictions: int = 0
    predictions_right: int = 0
    sparks: dict[str, int] = Field(default_factory=dict)       # concept -> stars (1-3)
    hall: list[HallEntry] = Field(default_factory=list)
    journal: list[int] = Field(default_factory=list)            # chapter ids whose lore is unlocked
    chapters_cleared: list[int] = Field(default_factory=list)   # this career
    chapter_scores: dict[str, int] = Field(default_factory=dict)  # this career: chapter id -> experiment score
    fixes: dict[str, str] = Field(default_factory=dict)          # this career: chapter id -> fix key kept
    run: dict | None = None                                       # this career: turn, energy, mood

    # ------------------------------------------------------------------ #

    @property
    def title(self) -> str:
        return [t for threshold, t in BOND_TITLES if self.bond >= threshold][-1]

    def concept(self, key: str) -> ConceptRecord:
        return self.concepts.setdefault(key, ConceptRecord())

    def add_bond(self, n: int) -> None:
        self.bond = max(0, min(100, self.bond + n))

    def schedule(self, key: str, correct: bool) -> None:
        rec = self.concept(key)
        rec.box = min(len(LEITNER_DAYS), rec.box + 1) if correct else 1
        rec.due_day = self.lab_day + LEITNER_DAYS[rec.box - 1]

    def due_concepts(self) -> list[str]:
        due = [(r.due_day, k) for k, r in self.concepts.items() if r.box > 0 and r.due_day <= self.lab_day]
        return [k for _, k in sorted(due)]

    def record_prediction(self, correct: bool, confidence: int) -> None:
        self.predictions += 1
        self.predictions_right += int(correct)
        if confidence >= 3:
            if correct:
                self.certain_right += 1
            else:
                self.certain_wrong += 1

    @property
    def calibration(self) -> float | None:
        n = self.certain_right + self.certain_wrong
        return round(self.certain_right / n, 2) if n else None

    def best_career(self) -> HallEntry | None:
        if not self.hall:
            return None
        return max(self.hall, key=lambda h: (sum(h.attributes.values()), -h.place))


class ProfileStore:
    """JSON file on disk, written atomically."""

    def __init__(self, path: str) -> None:
        self.path = path

    def load(self) -> Profile:
        try:
            with open(self.path) as fh:
                return Profile.model_validate(json.load(fh))
        except (OSError, ValueError):
            return Profile()

    def save(self, profile: Profile) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), suffix=".json")
        with os.fdopen(fd, "w") as fh:
            json.dump(profile.model_dump(), fh, indent=1)
        os.replace(tmp, self.path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

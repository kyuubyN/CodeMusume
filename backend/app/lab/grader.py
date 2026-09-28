"""Grade a spoken explanation against a chapter rubric of key ideas.

Transcripts are messy ("n plus one", "a sink", "time dot sleep"), so the text
is normalised before matching. The grader is deliberately transparent: it
reports which ideas were heard and which were missing, and Agnes turns the
missing ones into Socratic follow-up questions instead of handing over the
answer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.lab.chapters import KeyIdea

_SPOKEN = [
    (r"\bdot\b", "."), (r"\bunderscore\b", "_"), (r"\bn plus 1\b", "n+1"), (r"\bn plus one\b", "n+1"),
    (r"\ba sink\b", "async"), (r"\bay sink\b", "async"), (r"\bthe bounce\b", "debounce"),
    (r"\bjason\b", "json"), (r"\bsequel\b", "sql"), (r"\bf close\b", "f.close"),
]


def normalise(text: str) -> str:
    t = text.lower()
    for pat, rep in _SPOKEN:
        t = re.sub(pat, rep, t)
    t = re.sub(r"\s+\.\s+", ".", t)
    return t


@dataclass
class Grade:
    hits: list[str]
    missed: list[str]
    score: float          # 0..1
    follow_up: str | None


def grade(text: str, rubric: list[KeyIdea], already: set[str] | None = None) -> Grade:
    t = normalise(text)
    already = already or set()
    hits = [k.id for k in rubric if k.id in already or any(re.search(p, t) for p in k.patterns)]
    missed = [k for k in rubric if k.id not in hits]
    return Grade(
        hits=hits,
        missed=[k.id for k in missed],
        score=len(hits) / len(rubric) if rubric else 1.0,
        follow_up=missed[0].ask if missed else None,
    )

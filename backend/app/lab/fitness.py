"""Fitness functions: turn measurements of the trainee into stat scores.

Each stat maps one measured quantity onto a 0..1 quality on a log scale
between "as sick as the specimen ships" and "as good as it gets", then onto
the familiar 120..1120 stat range (G to S). The trainer's mastery of the
matching concept adds up to +80 on top, so SS needs both healthy code and a
trainer who understands why it is healthy.
"""
from __future__ import annotations

import math

from app.models.schemas import AttributeType

LO, HI = 120, 1120
MASTERY_BONUS = 80


def _log_quality(value: float, worst: float, best: float) -> float:
    value = max(value, 1e-9)
    if value <= best:
        return 1.0
    if value >= worst:
        return 0.0
    return (math.log(worst) - math.log(value)) / (math.log(worst) - math.log(best))


def quality(attribute: AttributeType, result: dict) -> float:
    m = result.get("metrics") or {}
    if "error" in result or not m:
        return 0.0
    if attribute == AttributeType.STAMINA:
        q = 1 / (1 + m.get("leaked_fds", 0) / 4)
        if m.get("us_per_request", 0) > 200:   # papering over a leak with gc.collect()
            q *= 0.9
        return q
    if attribute == AttributeType.SPEED:
        q = _log_quality(m.get("p99_ms", 2000), worst=1500, best=45)
        return q if m.get("errors", 0) == 0 else q * 0.5
    if attribute == AttributeType.POWER:
        q = _log_quality(m.get("queries", 201), worst=200, best=1)
        return q if m.get("correct", True) else 0.0
    if attribute == AttributeType.GUTS:
        n = max(1, m.get("requests", 40))
        honesty = max(0.0, 1 - 5 * m.get("silent_wrong", 0) / n)
        latency = _log_quality(m.get("p99_ms", 1200), worst=1150, best=150)
        return honesty * (0.4 + 0.6 * latency)
    if attribute == AttributeType.WISDOM:
        loaded = _linear(m.get("modules_loaded", 5), worst=5, best=3)
        acyclic = 1.0 if m.get("cycles", 1) == 0 else 0.0
        return (0.35 * acyclic + 0.65 * loaded) if m.get("correct", True) else 0.0
    return 0.0


def _linear(value: float, worst: float, best: float) -> float:
    if worst == best:
        return 1.0
    return max(0.0, min(1.0, (worst - value) / (worst - best)))


def score(attribute: AttributeType, result: dict, mastery: int = 0) -> int:
    base = LO + (HI - LO) * quality(attribute, result)
    return round(base + MASTERY_BONUS * max(0, min(100, mastery)) / 100)


def headline(result: dict) -> str:
    h = result.get("headline") or {}
    if not h:
        return result.get("error", "no data")
    return f"{h.get('value')} {h.get('unit', '')}".strip()

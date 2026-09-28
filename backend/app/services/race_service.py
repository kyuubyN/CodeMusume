"""URA Derby Race Simulation Engine — 2,000m in 100 ticks."""
from __future__ import annotations

import copy
import random
from typing import AsyncGenerator

from app.models.schemas import (
    AttributeScores,
    AttributeType,
    RaceIncident,
    RaceRival,
    RaceTick,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOTAL_TICKS: int = 100
RACE_DISTANCE_M: float = 2000.0

# Sector boundaries (in metres)
SECTOR_1_END: float = 500.0
SECTOR_2_END: float = 1200.0
SECTOR_3_END: float = 1600.0
SECTOR_4_END: float = 2000.0

# Attribute thresholds from spec
POWER_PENALTY_THRESHOLD: int = 450   # below → -20% tick speed in sector 2
GUTS_FREEZE_THRESHOLD: int = 400     # below → freeze 3 ticks in sector 3
WISDOM_GOLD_SKILL_THRESHOLD: int = 500  # above → Apex Domain Transcendence

# Tick speed: base metres per tick for the player (scales with Speed attribute)
_BASE_SPEED_M_PER_TICK: float = RACE_DISTANCE_M / TOTAL_TICKS  # = 20.0 m/tick

# Commentary pool
_MILESTONE_COMMENTARY: dict[int, str] = {
    25:  "The field spreads out after the opening burst — every millisecond counts now.",
    50:  "Halfway through the production derby! The traffic spike is incoming…",
    75:  "Database sector survived — the final stretch awaits. Push everything!",
    100: "The checkered flag drops. The race is over — results are in!",
}

_SECTOR_ACTIVATION_COMMENTARY: dict[str, str] = {
    "Batch Processing Turbo": (
        "Ufufu… *Batch Processing Turbo* activated! Concurrency is a beautiful drug."
    ),
    "Circuit Breaker Armor": (
        "Kukuku… *Circuit Breaker Armor* engaged. Resilience is its own reward."
    ),
    "Apex Domain Transcendence": (
        "The gold skill — *Apex Domain Transcendence* — blazes at the final stretch! "
        "This is what refined wisdom looks like, Morumotto-kun!"
    ),
}

# ---------------------------------------------------------------------------
# Rival definitions (immutable templates)
# ---------------------------------------------------------------------------

def _make_rivals() -> list[RaceRival]:
    return [
        RaceRival(
            id="legacy-monolith",
            name="Legacy Monolith",
            architecture_style="monolith",
            attributes=AttributeScores(
                speed=250, stamina=750, power=300, guts=150, wisdom=350
            ),
            current_distance=0.0,
            status="running",
        ),
        RaceRival(
            id="uncached-script",
            name="Uncached Script",
            architecture_style="script",
            attributes=AttributeScores(
                speed=650, stamina=120, power=200, guts=100, wisdom=150
            ),
            current_distance=0.0,
            status="running",
        ),
    ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _player_base_speed(attrs: AttributeScores) -> float:
    """Base metres-per-tick derived from Speed attribute (200 → 20 m/tick baseline)."""
    # Normalise so Speed 200 ≈ baseline 20 m/tick, Speed 1200 ≈ 26 m/tick
    speed_factor = 1.0 + (attrs.speed - 200) / 2000.0
    return _BASE_SPEED_M_PER_TICK * speed_factor


def _rival_speed(rival: RaceRival, current_distance: float) -> float:
    """Return metres-per-tick for a rival given its position."""
    attrs = rival.attributes
    base = _BASE_SPEED_M_PER_TICK

    if rival.id == "legacy-monolith":
        # Slow but steady — speed slightly below base, stamina irrelevant
        speed_factor = 1.0 + (attrs.speed - 200) / 3000.0
        return base * speed_factor

    if rival.id == "uncached-script":
        # Blazing fast early; severe stamina collapse after 800 m
        if current_distance < 800.0:
            speed_factor = 1.0 + (attrs.speed - 200) / 2000.0
        else:
            # Stamina exhausted — degrades proportionally to distance past 800 m
            exhaustion = min(1.0, (current_distance - 800.0) / 800.0)
            speed_factor = (1.0 + (attrs.speed - 200) / 2000.0) * (1.0 - 0.65 * exhaustion)
        return base * speed_factor

    # Generic runner (e.g. the ghost of a past career): paced like the player,
    # with the same stamina fade after 1,200 m.
    speed_factor = 1.0 + (attrs.speed - 200) / 2000.0
    if current_distance >= SECTOR_2_END:
        speed_factor *= max(0.85, 1.0 - (current_distance - 1200.0) / (max(attrs.stamina, 1) * 5.0))
    if SECTOR_1_END <= current_distance < SECTOR_2_END and attrs.power < POWER_PENALTY_THRESHOLD:
        speed_factor *= 0.80
    if current_distance >= SECTOR_3_END and attrs.wisdom >= WISDOM_GOLD_SKILL_THRESHOLD:
        speed_factor *= 1.30
    return base * speed_factor


def _tick_to_distance(tick: int) -> float:
    """Approximate race-progress distance at a given tick (0-indexed linear)."""
    return (tick / TOTAL_TICKS) * RACE_DISTANCE_M


def _sector_for(distance: float) -> int:
    if distance < SECTOR_1_END:
        return 1
    if distance < SECTOR_2_END:
        return 2
    if distance < SECTOR_3_END:
        return 3
    return 4


# ---------------------------------------------------------------------------
# Sector incident constructors
# ---------------------------------------------------------------------------

def _incident_sector2(player_power: int) -> RaceIncident:
    success = player_power >= POWER_PENALTY_THRESHOLD
    return RaceIncident(
        sector=2,
        distance_m=500.0,
        name="Traffic Spike (10k req/s)",
        tested_attribute=AttributeType.POWER,
        description=(
            "The load-balancer is drowning — 10,000 requests per second flood the cluster. "
            "Only batched, concurrent processing survives unscathed."
        ),
        player_success=success,
        tachyon_callout=(
            _SECTOR_ACTIVATION_COMMENTARY["Batch Processing Turbo"]
            if success
            else (
                "Kukuku… sequential processing at scale — how delightfully catastrophic. "
                "You're haemorrhaging latency by the millisecond."
            )
        ),
    )


def _incident_sector3(player_guts: int) -> RaceIncident:
    success = player_guts >= GUTS_FREEZE_THRESHOLD
    return RaceIncident(
        sector=3,
        distance_m=1200.0,
        name="Database Connection Drop",
        tested_attribute=AttributeType.GUTS,
        description=(
            "The primary database vanishes mid-race. Circuit breakers must fire instantly "
            "or the whole service freezes waiting for a connection that will never come."
        ),
        player_success=success,
        tachyon_callout=(
            _SECTOR_ACTIVATION_COMMENTARY["Circuit Breaker Armor"]
            if success
            else (
                "Kukuku… no circuit breaker, no resilience. The specimen stumbles. "
                "Three ticks lost to an unhandled timeout — fascinating how expensive fear is."
            )
        ),
    )


def _incident_sector4(player_wisdom: int) -> RaceIncident:
    success = player_wisdom >= WISDOM_GOLD_SKILL_THRESHOLD
    return RaceIncident(
        sector=4,
        distance_m=1600.0,
        name="Final Sprint — Apex Domain Transcendence",
        tested_attribute=AttributeType.WISDOM,
        description=(
            "The final 400m — pure architectural clarity separates the legends from the legacy. "
            "Only deep domain wisdom unlocks the gold skill."
        ),
        player_success=success,
        tachyon_callout=(
            _SECTOR_ACTIVATION_COMMENTARY["Apex Domain Transcendence"]
            if success
            else (
                "No gold skill today. The final stretch is run on raw stamina alone — "
                "a missed opportunity, Morumotto-kun."
            )
        ),
    )


# ---------------------------------------------------------------------------
# RaceSimulator
# ---------------------------------------------------------------------------

class RaceSimulator:
    """Simulates the 2,000-meter URA Production Derby in 100 ticks."""

    def __init__(self, player_attributes: AttributeScores, rivals: list[RaceRival] | None = None) -> None:
        self.player_attributes = player_attributes
        self._rivals = rivals
        # Pre-compute incidents once so they're consistent across the simulation
        self._incident_s2 = _incident_sector2(player_attributes.power)
        self._incident_s3 = _incident_sector3(player_attributes.guts)
        self._incident_s4 = _incident_sector4(player_attributes.wisdom)

    # ------------------------------------------------------------------ #

    def run_simulation(self) -> list[RaceTick]:
        """Simulate the full race and return all 100 RaceTick objects (1-indexed)."""
        attrs = self.player_attributes
        rivals = [r.model_copy(deep=True) for r in self._rivals] if self._rivals else _make_rivals()

        player_distance: float = 0.0
        player_frozen_ticks: int = 0      # remaining freeze ticks from sector-3 incident
        power_penalty_active: bool = False
        gold_skill_active: bool = False
        # Track which sector incidents have already been emitted
        incident_emitted: set[int] = set()

        ticks: list[RaceTick] = []

        for tick in range(1, TOTAL_TICKS + 1):

            # ---- Player tick speed calculation ----
            speed_m = _player_base_speed(attrs)

            # Sector 2: Power check
            if player_distance >= SECTOR_1_END and 2 not in incident_emitted:
                incident_emitted.add(2)
                power_penalty_active = attrs.power < POWER_PENALTY_THRESHOLD

            # Sector 3: Guts check
            if player_distance >= SECTOR_2_END and 3 not in incident_emitted:
                incident_emitted.add(3)
                if attrs.guts < GUTS_FREEZE_THRESHOLD:
                    player_frozen_ticks = 3

            # Sector 4: Wisdom / gold skill
            if player_distance >= SECTOR_3_END and 4 not in incident_emitted:
                incident_emitted.add(4)
                if attrs.wisdom >= WISDOM_GOLD_SKILL_THRESHOLD:
                    gold_skill_active = True

            # Apply modifiers
            if player_frozen_ticks > 0:
                player_frozen_ticks -= 1
                speed_m = 0.0                        # full freeze
            elif power_penalty_active:
                speed_m *= 0.80                      # -20% in sector 2 failure
            elif gold_skill_active:
                speed_m *= 1.30                      # +30% gold skill

            # Stamina scaling: small degradation after 1200 m for the player
            if player_distance >= SECTOR_2_END:
                stamina_factor = max(0.85, 1.0 - (player_distance - 1200.0) /
                                     (attrs.stamina * 5.0))
                speed_m *= stamina_factor

            player_distance = min(RACE_DISTANCE_M, player_distance + speed_m)

            # ---- Rival movements ----
            updated_rivals: list[RaceRival] = []
            for rival in rivals:
                if rival.status == "finished":
                    updated_rivals.append(rival)
                    continue
                rival_speed = _rival_speed(rival, rival.current_distance)
                new_dist = min(RACE_DISTANCE_M, rival.current_distance + rival_speed)
                new_status = "finished" if new_dist >= RACE_DISTANCE_M else "running"
                updated_rivals.append(rival.model_copy(update={
                    "current_distance": new_dist,
                    "status": new_status,
                }))
            rivals = updated_rivals

            # ---- Active incident (only at entry ticks) ----
            active_incident: RaceIncident | None = None
            sector = _sector_for(player_distance)
            if sector == 2 and 2 in incident_emitted and tick == next(
                (t for t in range(1, TOTAL_TICKS + 1)
                 if _sector_for(_player_base_speed(attrs) * t) >= 2), tick
            ):
                pass  # incident already assigned; show at entry tick

            # Emit incidents at the tick they first become relevant
            if sector == 2 and len(incident_emitted) == 1 and 2 in incident_emitted:
                # Just entered sector 2 this tick
                active_incident = self._incident_s2
                incident_emitted.add(-2)    # mark as displayed
            if sector == 3 and len([x for x in incident_emitted if x > 0]) == 2 \
                    and 3 in incident_emitted and -3 not in incident_emitted:
                active_incident = self._incident_s3
                incident_emitted.add(-3)
            if sector == 4 and 4 in incident_emitted and -4 not in incident_emitted:
                active_incident = self._incident_s4
                incident_emitted.add(-4)

            # ---- Commentary at milestone ticks ----
            commentary: str | None = _MILESTONE_COMMENTARY.get(tick)

            # ---- is_finished ----
            all_finished = (
                player_distance >= RACE_DISTANCE_M
                and all(r.current_distance >= RACE_DISTANCE_M for r in rivals)
            )
            is_finished = tick == TOTAL_TICKS or all_finished

            ticks.append(RaceTick(
                tick=tick,
                distance_m=round(player_distance, 2),
                player_distance=round(player_distance, 2),
                rivals=rivals,
                active_incident=active_incident,
                commentary=commentary,
                is_finished=is_finished,
            ))

            if is_finished:
                break

        # Pad to exactly 100 ticks if the race finished early
        if len(ticks) < TOTAL_TICKS and ticks:
            last = ticks[-1]
            for pad_tick in range(len(ticks) + 1, TOTAL_TICKS + 1):
                ticks.append(last.model_copy(update={
                    "tick": pad_tick,
                    "is_finished": True,
                    "commentary": None,
                    "active_incident": None,
                }))

        return ticks

    # ------------------------------------------------------------------ #

    async def stream_simulation(self) -> AsyncGenerator[RaceTick, None]:
        """Async generator yielding each RaceTick for Server-Sent Events."""
        for tick in self.run_simulation():
            yield tick

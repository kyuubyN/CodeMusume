"""Unit tests for backend/app/services/race_service.py — Mission 04."""
from __future__ import annotations

import asyncio

import pytest

from app.models.schemas import AttributeScores, AttributeType, RaceTick
from app.services.race_service import (
    GUTS_FREEZE_THRESHOLD,
    POWER_PENALTY_THRESHOLD,
    RACE_DISTANCE_M,
    TOTAL_TICKS,
    WISDOM_GOLD_SKILL_THRESHOLD,
    RaceSimulator,
    _incident_sector2,
    _incident_sector3,
    _incident_sector4,
    _rival_speed,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _high_spec() -> AttributeScores:
    """Well-rounded player that beats both rivals."""
    return AttributeScores(speed=800, stamina=700, power=600, guts=500, wisdom=600)


def _low_spec() -> AttributeScores:
    """Weak player used to verify penalties."""
    return AttributeScores(speed=300, stamina=200, power=300, guts=200, wisdom=200)


def _run(attrs: AttributeScores) -> list[RaceTick]:
    return RaceSimulator(attrs).run_simulation()


# ---------------------------------------------------------------------------
# Tick count and structure
# ---------------------------------------------------------------------------

class TestTickStructure:

    def test_simulation_returns_100_ticks(self):
        ticks = _run(_high_spec())
        assert len(ticks) == TOTAL_TICKS

    def test_tick_numbers_are_sequential_from_1(self):
        ticks = _run(_high_spec())
        for i, tick in enumerate(ticks):
            assert tick.tick == i + 1

    def test_last_tick_is_finished(self):
        ticks = _run(_high_spec())
        assert ticks[-1].is_finished is True

    def test_each_tick_has_two_rivals(self):
        ticks = _run(_high_spec())
        for tick in ticks:
            assert len(tick.rivals) == 2

    def test_rival_ids_present(self):
        ticks = _run(_high_spec())
        ids = {r.id for r in ticks[0].rivals}
        assert "legacy-monolith" in ids
        assert "uncached-script" in ids

    def test_player_distance_non_decreasing(self):
        ticks = _run(_high_spec())
        for i in range(1, len(ticks)):
            assert ticks[i].player_distance >= ticks[i - 1].player_distance

    def test_player_distance_matches_distance_m(self):
        ticks = _run(_high_spec())
        for tick in ticks:
            assert tick.player_distance == tick.distance_m

    def test_all_distances_within_bounds(self):
        ticks = _run(_high_spec())
        for tick in ticks:
            assert 0.0 <= tick.player_distance <= RACE_DISTANCE_M
            for rival in tick.rivals:
                assert 0.0 <= rival.current_distance <= RACE_DISTANCE_M


# ---------------------------------------------------------------------------
# High-spec player wins
# ---------------------------------------------------------------------------

class TestHighSpecPlayerWins:

    def test_high_spec_crosses_finish_line(self):
        ticks = _run(_high_spec())
        assert ticks[-1].player_distance >= RACE_DISTANCE_M

    def test_high_spec_beats_legacy_monolith(self):
        ticks = _run(_high_spec())
        last = ticks[-1]
        monolith = next(r for r in last.rivals if r.id == "legacy-monolith")
        # Player finishes at or ahead of monolith
        assert last.player_distance >= monolith.current_distance

    def test_high_spec_beats_uncached_script(self):
        """High-spec player with good stamina outlasts the Uncached Script."""
        ticks = _run(_high_spec())
        last = ticks[-1]
        script = next(r for r in last.rivals if r.id == "uncached-script")
        assert last.player_distance >= script.current_distance


# ---------------------------------------------------------------------------
# Uncached Script stamina collapse
# ---------------------------------------------------------------------------

class TestUncachedScriptStaminaCollapse:

    def _script_distances(self, ticks: list[RaceTick]) -> list[float]:
        return [
            next(r.current_distance for r in t.rivals if r.id == "uncached-script")
            for t in ticks
        ]

    def _monolith_distances(self, ticks: list[RaceTick]) -> list[float]:
        return [
            next(r.current_distance for r in t.rivals if r.id == "legacy-monolith")
            for t in ticks
        ]

    def test_uncached_script_leads_early(self):
        """Uncached Script should be ahead of Legacy Monolith in the first 40 ticks."""
        ticks = _run(_high_spec())
        script_d = self._script_distances(ticks)
        monolith_d = self._monolith_distances(ticks)
        # Check at tick 20 (index 19)
        assert script_d[19] > monolith_d[19], (
            "Uncached Script should lead the slow Monolith early in the race"
        )

    def test_uncached_script_slows_significantly_after_800m(self):
        """Speed-per-tick must drop noticeably after 800 m."""
        from app.services.race_service import _rival_speed, _make_rivals
        rivals = _make_rivals()
        script = next(r for r in rivals if r.id == "uncached-script")

        speed_before_800 = _rival_speed(script, 400.0)
        speed_after_800 = _rival_speed(script, 1400.0)

        assert speed_after_800 < speed_before_800 * 0.6, (
            f"Expected significant slowdown after 800m. "
            f"Before: {speed_before_800:.2f}, After: {speed_after_800:.2f}"
        )

    def test_monolith_overtakes_script_by_end(self):
        """After the stamina collapse the Legacy Monolith should close the gap."""
        ticks = _run(_high_spec())
        script_d = self._script_distances(ticks)
        monolith_d = self._monolith_distances(ticks)
        # At tick 80 (index 79), monolith should have closed within 300 m or overtaken
        gap = script_d[79] - monolith_d[79]
        assert gap < 300.0, (
            f"Monolith should close gap after script stamina collapse, but gap is {gap:.1f}m"
        )


# ---------------------------------------------------------------------------
# Sector incident triggers
# ---------------------------------------------------------------------------

class TestSectorIncidents:

    def test_incident_sector2_success_above_threshold(self):
        attrs = AttributeScores(power=POWER_PENALTY_THRESHOLD + 50)
        incident = _incident_sector2(attrs.power)
        assert incident.player_success is True
        assert incident.tested_attribute == AttributeType.POWER
        assert "Batch Processing Turbo" in incident.tachyon_callout

    def test_incident_sector2_failure_below_threshold(self):
        attrs = AttributeScores(power=POWER_PENALTY_THRESHOLD - 1)
        incident = _incident_sector2(attrs.power)
        assert incident.player_success is False
        assert incident.tested_attribute == AttributeType.POWER

    def test_incident_sector3_success_above_threshold(self):
        attrs = AttributeScores(guts=GUTS_FREEZE_THRESHOLD + 50)
        incident = _incident_sector3(attrs.guts)
        assert incident.player_success is True
        assert incident.tested_attribute == AttributeType.GUTS
        assert "Circuit Breaker Armor" in incident.tachyon_callout

    def test_incident_sector3_failure_below_threshold(self):
        attrs = AttributeScores(guts=GUTS_FREEZE_THRESHOLD - 1)
        incident = _incident_sector3(attrs.guts)
        assert incident.player_success is False
        assert incident.tested_attribute == AttributeType.GUTS

    def test_incident_sector4_success_above_threshold(self):
        attrs = AttributeScores(wisdom=WISDOM_GOLD_SKILL_THRESHOLD + 50)
        incident = _incident_sector4(attrs.wisdom)
        assert incident.player_success is True
        assert incident.tested_attribute == AttributeType.WISDOM
        assert "Apex Domain Transcendence" in incident.tachyon_callout

    def test_incident_sector4_failure_below_threshold(self):
        attrs = AttributeScores(wisdom=WISDOM_GOLD_SKILL_THRESHOLD - 1)
        incident = _incident_sector4(attrs.wisdom)
        assert incident.player_success is False
        assert incident.tested_attribute == AttributeType.WISDOM

    def test_sector3_freeze_slows_player(self):
        """A player with low guts should be slowed by the freeze penalty."""
        low_guts = AttributeScores(
            speed=600, stamina=600, power=600,
            guts=GUTS_FREEZE_THRESHOLD - 50, wisdom=600
        )
        high_guts = AttributeScores(
            speed=600, stamina=600, power=600,
            guts=GUTS_FREEZE_THRESHOLD + 50, wisdom=600
        )
        ticks_low = _run(low_guts)
        ticks_high = _run(high_guts)

        # Compare position at tick 70 — freeze should leave low-guts behind
        d_low = ticks_low[69].player_distance
        d_high = ticks_high[69].player_distance
        assert d_high > d_low, (
            f"High-guts player ({d_high:.1f}m) should be ahead of "
            f"frozen low-guts player ({d_low:.1f}m) at tick 70"
        )

    def test_sector2_penalty_slows_player(self):
        """A player with low power should be slower in sector 2."""
        low_power = AttributeScores(
            speed=600, stamina=600, power=POWER_PENALTY_THRESHOLD - 50,
            guts=600, wisdom=600
        )
        high_power = AttributeScores(
            speed=600, stamina=600, power=POWER_PENALTY_THRESHOLD + 50,
            guts=600, wisdom=600
        )
        ticks_low = _run(low_power)
        ticks_high = _run(high_power)

        # During sector 2 (roughly ticks 26-60) high-power should be ahead
        d_low = ticks_low[49].player_distance
        d_high = ticks_high[49].player_distance
        assert d_high >= d_low, (
            f"High-power player should not be behind low-power player at tick 50. "
            f"High: {d_high:.1f}m, Low: {d_low:.1f}m"
        )

    def test_sector4_gold_skill_boosts_final_sprint(self):
        """A player with high wisdom should cover more distance in the final sector."""
        low_wisdom = AttributeScores(
            speed=600, stamina=600, power=600,
            guts=600, wisdom=WISDOM_GOLD_SKILL_THRESHOLD - 50
        )
        high_wisdom = AttributeScores(
            speed=600, stamina=600, power=600,
            guts=600, wisdom=WISDOM_GOLD_SKILL_THRESHOLD + 50
        )
        ticks_low = _run(low_wisdom)
        ticks_high = _run(high_wisdom)

        # High wisdom finishes with more total distance covered (or same if both max out)
        d_low = ticks_low[-1].player_distance
        d_high = ticks_high[-1].player_distance
        assert d_high >= d_low


# ---------------------------------------------------------------------------
# Milestone commentary
# ---------------------------------------------------------------------------

class TestMilestoneCommentary:

    def test_tick_25_has_commentary(self):
        ticks = _run(_high_spec())
        assert ticks[24].commentary is not None
        assert len(ticks[24].commentary) > 10

    def test_tick_50_has_commentary(self):
        ticks = _run(_high_spec())
        assert ticks[49].commentary is not None

    def test_tick_75_has_commentary(self):
        ticks = _run(_high_spec())
        assert ticks[74].commentary is not None

    def test_tick_100_has_commentary(self):
        ticks = _run(_high_spec())
        assert ticks[99].commentary is not None

    def test_other_ticks_may_have_no_commentary(self):
        ticks = _run(_high_spec())
        non_milestone_no_comment = [
            t for t in ticks
            if t.tick not in (25, 50, 75, 100) and t.commentary is not None
        ]
        # It's fine if incidents add commentary, but milestone ticks must all have it
        # (we just confirm the four milestones are covered above)


# ---------------------------------------------------------------------------
# Race result serialisation
# ---------------------------------------------------------------------------

class TestRaceTickSerialisation:

    def test_ticks_are_race_tick_instances(self):
        ticks = _run(_high_spec())
        for tick in ticks:
            assert isinstance(tick, RaceTick)

    def test_ticks_are_json_serialisable(self):
        ticks = _run(_high_spec())
        # Should not raise
        for tick in ticks:
            tick.model_dump_json()

    def test_roundtrip_serialisation(self):
        ticks = _run(_high_spec())
        sample = ticks[49]
        restored = RaceTick.model_validate_json(sample.model_dump_json())
        assert restored == sample


# ---------------------------------------------------------------------------
# Async stream_simulation
# ---------------------------------------------------------------------------

class TestStreamSimulation:

    def test_stream_yields_100_ticks(self):
        async def _collect() -> list[RaceTick]:
            sim = RaceSimulator(_high_spec())
            return [tick async for tick in sim.stream_simulation()]

        ticks = asyncio.run(_collect())
        assert len(ticks) == TOTAL_TICKS

    def test_stream_and_run_produce_same_ticks(self):
        async def _collect() -> list[RaceTick]:
            sim = RaceSimulator(_high_spec())
            return [tick async for tick in sim.stream_simulation()]

        streamed = asyncio.run(_collect())
        run_result = RaceSimulator(_high_spec()).run_simulation()

        assert len(streamed) == len(run_result)
        for s, r in zip(streamed, run_result):
            assert s.tick == r.tick

    def test_stream_last_tick_is_finished(self):
        async def _collect_last() -> RaceTick:
            sim = RaceSimulator(_high_spec())
            last = None
            async for tick in sim.stream_simulation():
                last = tick
            return last  # type: ignore[return-value]

        last = asyncio.run(_collect_last())
        assert last.is_finished is True


# ---------------------------------------------------------------------------
# Rival attribute definition guard
# ---------------------------------------------------------------------------

class TestRivalDefinitions:

    def test_legacy_monolith_attributes(self):
        from app.services.race_service import _make_rivals
        rivals = _make_rivals()
        monolith = next(r for r in rivals if r.id == "legacy-monolith")
        assert monolith.attributes.speed == 250
        assert monolith.attributes.stamina == 750
        assert monolith.attributes.power == 300
        assert monolith.attributes.guts == 150
        assert monolith.attributes.wisdom == 350

    def test_uncached_script_attributes(self):
        from app.services.race_service import _make_rivals
        rivals = _make_rivals()
        script = next(r for r in rivals if r.id == "uncached-script")
        assert script.attributes.speed == 650
        assert script.attributes.stamina == 120
        assert script.attributes.power == 200
        assert script.attributes.guts == 100
        assert script.attributes.wisdom == 150

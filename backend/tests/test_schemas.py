"""Unit tests for backend/app/models/schemas.py — Mission 01."""
import pytest

from app.models.schemas import (
    AttributeScores,
    AttributeType,
    AvatarPose,
    GameState,
    MoodState,
    RaceIncident,
    RaceRival,
    RaceTick,
    StatRank,
    TrainResult,
    score_to_rank,
)


# ---------------------------------------------------------------------------
# score_to_rank thresholds
# ---------------------------------------------------------------------------

class TestScoreToRank:
    def test_g_lower_bound(self):
        assert score_to_rank(0) == StatRank.G

    def test_g_upper_bound(self):
        assert score_to_rank(199) == StatRank.G

    def test_f_lower_bound(self):
        assert score_to_rank(200) == StatRank.F

    def test_f_upper_bound(self):
        assert score_to_rank(399) == StatRank.F

    def test_e(self):
        assert score_to_rank(400) == StatRank.E
        assert score_to_rank(499) == StatRank.E

    def test_d_lower_bound(self):
        assert score_to_rank(500) == StatRank.D

    def test_d_upper_bound(self):
        assert score_to_rank(599) == StatRank.D

    def test_c(self):
        assert score_to_rank(600) == StatRank.C
        assert score_to_rank(699) == StatRank.C

    def test_b_lower_bound(self):
        assert score_to_rank(700) == StatRank.B

    def test_b_upper_bound(self):
        assert score_to_rank(799) == StatRank.B

    def test_a(self):
        assert score_to_rank(800) == StatRank.A
        assert score_to_rank(999) == StatRank.A

    def test_s_lower_bound(self):
        assert score_to_rank(1000) == StatRank.S

    def test_s_upper_bound(self):
        assert score_to_rank(1149) == StatRank.S

    def test_ss_lower_bound(self):
        assert score_to_rank(1150) == StatRank.SS

    def test_ss_high(self):
        assert score_to_rank(9999) == StatRank.SS


# ---------------------------------------------------------------------------
# AttributeScores.get_ranks()
# ---------------------------------------------------------------------------

class TestAttributeScoresGetRanks:
    def test_defaults_all_f(self):
        scores = AttributeScores()
        ranks = scores.get_ranks()
        assert ranks == {
            "speed": StatRank.F,
            "stamina": StatRank.F,
            "power": StatRank.F,
            "guts": StatRank.F,
            "wisdom": StatRank.F,
        }

    def test_mixed_ranks(self):
        scores = AttributeScores(speed=100, stamina=500, power=750, guts=1000, wisdom=1200)
        ranks = scores.get_ranks()
        assert ranks["speed"] == StatRank.G
        assert ranks["stamina"] == StatRank.D
        assert ranks["power"] == StatRank.B
        assert ranks["guts"] == StatRank.S
        assert ranks["wisdom"] == StatRank.SS

    def test_keys_present(self):
        ranks = AttributeScores().get_ranks()
        assert set(ranks.keys()) == {"speed", "stamina", "power", "guts", "wisdom"}


# ---------------------------------------------------------------------------
# Default GameState values and mutations
# ---------------------------------------------------------------------------

class TestGameStateDefaults:
    def test_default_values(self):
        state = GameState()
        assert state.repo_name == "code-musume"
        assert state.turn == 1
        assert state.max_turns == 12
        assert state.energy == 100
        assert state.mood == MoodState.NORMAL
        assert state.current_pose == AvatarPose.idle
        assert state.dialogue == ""
        assert state.is_game_over is False

    def test_default_attributes_are_attribute_scores(self):
        state = GameState()
        assert isinstance(state.attributes, AttributeScores)

    def test_mutation(self):
        state = GameState()
        state.turn = 5
        state.energy = 40
        state.mood = MoodState.GOOD
        state.is_game_over = True
        assert state.turn == 5
        assert state.energy == 40
        assert state.mood == MoodState.GOOD
        assert state.is_game_over is True

    def test_energy_constraint_min(self):
        with pytest.raises(Exception):
            GameState(energy=-1)

    def test_energy_constraint_max(self):
        with pytest.raises(Exception):
            GameState(energy=101)


# ---------------------------------------------------------------------------
# TrainResult serialization
# ---------------------------------------------------------------------------

class TestTrainResultSerialization:
    def _make_train_result(self) -> TrainResult:
        return TrainResult(
            success=True,
            attribute=AttributeType.SPEED,
            stat_gained=15,
            energy_spent=20,
            failure_rate=0.1,
            tachyon_commentary="Splendid result, as expected!",
            pose=AvatarPose.happy,
            updated_state=GameState(turn=2, energy=80),
        )

    def test_model_dump_contains_expected_keys(self):
        result = self._make_train_result()
        data = result.model_dump()
        expected_keys = {
            "success", "attribute", "stat_gained", "energy_spent",
            "failure_rate", "tachyon_commentary", "pose", "updated_state",
        }
        assert expected_keys.issubset(data.keys())

    def test_model_dump_values(self):
        result = self._make_train_result()
        data = result.model_dump()
        assert data["success"] is True
        assert data["attribute"] == AttributeType.SPEED
        assert data["stat_gained"] == 15
        assert data["energy_spent"] == 20
        assert data["failure_rate"] == pytest.approx(0.1)
        assert data["updated_state"]["turn"] == 2

    def test_roundtrip_json(self):
        result = self._make_train_result()
        json_str = result.model_dump_json()
        restored = TrainResult.model_validate_json(json_str)
        assert restored == result


# ---------------------------------------------------------------------------
# RaceTick serialization
# ---------------------------------------------------------------------------

class TestRaceTickSerialization:
    def _make_rival(self) -> RaceRival:
        return RaceRival(
            id="rival-001",
            name="Silence Suzuka",
            architecture_style="monolith",
            attributes=AttributeScores(speed=800, stamina=700, power=600, guts=500, wisdom=400),
            current_distance=500.0,
            status="running",
        )

    def _make_incident(self) -> RaceIncident:
        return RaceIncident(
            sector=1,
            distance_m=300.0,
            name="CI Pipeline Outage",
            tested_attribute=AttributeType.WISDOM,
            description="Tests are failing in production!",
            player_success=True,
            tachyon_callout="Fascinating… you handled it.",
        )

    def test_no_incident_defaults(self):
        tick = RaceTick(
            tick=0,
            distance_m=0.0,
            player_distance=0.0,
            rivals=[self._make_rival()],
        )
        assert tick.active_incident is None
        assert tick.commentary is None
        assert tick.is_finished is False

    def test_with_incident(self):
        incident = self._make_incident()
        tick = RaceTick(
            tick=50,
            distance_m=1000.0,
            player_distance=980.0,
            rivals=[self._make_rival()],
            active_incident=incident,
            commentary="Neck and neck at the halfway mark!",
        )
        assert tick.active_incident == incident
        assert tick.commentary == "Neck and neck at the halfway mark!"

    def test_model_dump_keys(self):
        tick = RaceTick(
            tick=100,
            distance_m=2000.0,
            player_distance=1980.0,
            rivals=[self._make_rival()],
            is_finished=True,
        )
        data = tick.model_dump()
        expected_keys = {
            "tick", "distance_m", "player_distance", "rivals",
            "active_incident", "commentary", "is_finished",
        }
        assert expected_keys == set(data.keys())

    def test_roundtrip_json(self):
        tick = RaceTick(
            tick=25,
            distance_m=500.0,
            player_distance=490.0,
            rivals=[self._make_rival()],
            active_incident=self._make_incident(),
            commentary="Go!",
        )
        json_str = tick.model_dump_json()
        restored = RaceTick.model_validate_json(json_str)
        assert restored == tick

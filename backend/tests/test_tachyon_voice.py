"""Unit tests for Dr. Agnes Tachyon Japanese Personality, Catchphrases & Mood Mapping Engine."""
from __future__ import annotations

import pytest

from app.data.tachyon_catchphrases import (
    CANONICAL_DIALOGUES,
    MOOD_ACOUSTIC_PROFILES,
    SIGNATURE_CATCHPHRASES,
    TACHYON_NAME_JP,
    THEMATIC_TERMS_MAP,
    TRAINER_TERMS_JP,
    MoodAcousticProfile,
    normalize_mood_name,
)
from app.models.schemas import AvatarPose, MoodState
from app.services.tachyon_voice import TachyonVoiceEngine


class TestMoodAcousticProfiles:
    """Verify acoustic profiles and cadence parameters for all 6 required character moods."""

    @pytest.mark.parametrize(
        "mood,min_speed,max_speed,min_pitch,max_pitch",
        [
            ("flow", 1.10, 1.25, 0.5, 2.0),
            ("happy", 1.02, 1.15, 0.1, 1.0),
            ("thinking", 0.90, 1.00, -1.0, 0.0),
            ("shocked", 1.10, 1.25, 1.5, 3.0),
            ("serious", 0.98, 1.05, -1.5, -0.2),
            ("tired", 0.80, 0.92, -2.5, -1.0),
        ],
    )
    def test_mood_acoustic_parameters_boundaries(
        self,
        mood: str,
        min_speed: float,
        max_speed: float,
        min_pitch: float,
        max_pitch: float,
    ) -> None:
        profile = TachyonVoiceEngine.get_mood_profile(mood)
        assert isinstance(profile, MoodAcousticProfile)
        assert min_speed <= profile.speed <= max_speed
        assert min_pitch <= profile.pitch_semitones <= max_pitch
        assert profile.voice == "jf_nezumi"
        assert "jf_nezumi" in profile.voice_mix
        assert len(profile.prefixes) >= 3
        assert len(profile.suffixes) >= 3
        assert len(profile.subtitle_cues) >= 3
        assert len(profile.romanized_cues) >= 3

    def test_cadence_pause_scales(self) -> None:
        """Shocked and flow should have quick cadence (low pause_scale), tired should have drawn out pauses."""
        shocked_profile = TachyonVoiceEngine.get_mood_profile("shocked")
        flow_profile = TachyonVoiceEngine.get_mood_profile("flow")
        thinking_profile = TachyonVoiceEngine.get_mood_profile("thinking")
        tired_profile = TachyonVoiceEngine.get_mood_profile("tired")

        assert shocked_profile.pause_scale < 0.80
        assert flow_profile.pause_scale < 0.80
        assert thinking_profile.pause_scale > 1.0
        assert tired_profile.pause_scale >= 1.30


class TestMoodNormalization:
    """Verify normalization handles strings, AvatarPose enums, MoodState enums, and fallbacks."""

    def test_canonical_mood_strings(self) -> None:
        canonical = ["flow", "happy", "thinking", "shocked", "serious", "tired"]
        for mood in canonical:
            assert TachyonVoiceEngine.normalize_mood(mood) == mood
            assert TachyonVoiceEngine.normalize_mood(mood.upper()) == mood

    def test_avatar_pose_enum_normalization(self) -> None:
        assert TachyonVoiceEngine.normalize_mood(AvatarPose.flow) == "flow"
        assert TachyonVoiceEngine.normalize_mood(AvatarPose.happy) == "happy"
        assert TachyonVoiceEngine.normalize_mood(AvatarPose.thinking) == "thinking"
        assert TachyonVoiceEngine.normalize_mood(AvatarPose.shocked) == "shocked"
        assert TachyonVoiceEngine.normalize_mood(AvatarPose.serious) == "serious"
        assert TachyonVoiceEngine.normalize_mood(AvatarPose.tired) == "tired"
        assert TachyonVoiceEngine.normalize_mood(AvatarPose.idle) == "thinking"

    def test_mood_state_enum_normalization(self) -> None:
        assert TachyonVoiceEngine.normalize_mood(MoodState.GREAT) == "flow"
        assert TachyonVoiceEngine.normalize_mood(MoodState.GOOD) == "happy"
        assert TachyonVoiceEngine.normalize_mood(MoodState.NORMAL) == "thinking"
        assert TachyonVoiceEngine.normalize_mood(MoodState.POOR) == "serious"
        assert TachyonVoiceEngine.normalize_mood(MoodState.TERRIBLE) == "tired"

    def test_fallback_for_unknown_or_empty_mood(self) -> None:
        assert TachyonVoiceEngine.normalize_mood("") == "thinking"
        assert TachyonVoiceEngine.normalize_mood(None) == "thinking"
        assert TachyonVoiceEngine.normalize_mood("unknown_mood_state") == "thinking"


class TestCatchphrasesAndCharacterLexicon:
    """Verify Agnes Tachyon's signature catchphrases and character terms."""

    def test_signature_catchphrases_exist(self) -> None:
        catchphrases = TachyonVoiceEngine.get_all_catchphrases()
        assert len(catchphrases) >= 7

        required_catchphrases = [
            "我がモルモット君！",
            "興味深いねぇ...",
            "アッハハハ！",
            "実験開始だ！",
            "私の光彩が見えるかい？",
            "ククク…",
        ]
        for cp in required_catchphrases:
            assert cp in catchphrases or any(cp in item for item in catchphrases)

    def test_trainer_address_terms(self) -> None:
        assert "我がモルモット君" in TRAINER_TERMS_JP
        assert "モルモット君" in TRAINER_TERMS_JP

    def test_japanese_name_and_title(self) -> None:
        assert TACHYON_NAME_JP == "アグネスタキオン"
        assert "アーキテクト" in THEMATIC_TERMS_MAP["architect"]


class TestJapaneseDialogueTransformation:
    """Verify transformation of dialogue into Agnes Tachyon's Japanese anime persona."""

    def test_canonical_dialogue_matching(self) -> None:
        # Greetings
        greeting_text = "Greetings, Morumotto-kun! Let our grand software experiment commence!"
        jp_greeting = TachyonVoiceEngine.transform_dialogue_to_japanese(greeting_text)
        assert "我がモルモット君" in jp_greeting
        assert "アグネスタキオン" in jp_greeting or "実験" in jp_greeting

        # Rest
        rest_text = "Recovery time: Rest is not laziness, take a rest."
        jp_rest = TachyonVoiceEngine.transform_dialogue_to_japanese(rest_text)
        assert "休息" in jp_rest
        assert "紅茶" in jp_rest

        # Failure / Anomaly
        fail_text = "Catastrophic metabolic failure during training run."
        jp_fail = TachyonVoiceEngine.transform_dialogue_to_japanese(fail_text)
        assert "プランB" in jp_fail or "特異点" in jp_fail

        # Victory
        victory_text = "Synthesized the cure: Grand Derby victory achieved!"
        jp_victory = TachyonVoiceEngine.transform_dialogue_to_japanese(victory_text)
        assert "私の光彩が見えるかい？" in jp_victory or "限界の先" in jp_victory

    def test_thematic_enterprise_keywords_injected(self) -> None:
        text = "Refactoring the architecture of the database and cache service."
        jp_text = TachyonVoiceEngine.transform_dialogue_to_japanese(text, mood="thinking")
        assert "アーキテクチャ" in jp_text or "リファクタリング" in jp_text or "データベース" in jp_text
        assert any(term in jp_text for term in ["モルモット君", "興味深い", "分析", "検証", "ほぉ", "ふむ"])

    def test_pure_japanese_text_preservation(self) -> None:
        original_jp = "ククク… 我が理論の進捗を見守るとしよう！"
        result = TachyonVoiceEngine.transform_dialogue_to_japanese(original_jp, mood="flow")
        assert original_jp in result

    def test_japanese_detection_helper(self) -> None:
        assert TachyonVoiceEngine.is_japanese_text("こんにちは")
        assert TachyonVoiceEngine.is_japanese_text("Kukuku... 我がモルモット君")
        assert not TachyonVoiceEngine.is_japanese_text("Hello Enterprise Architect")
        assert not TachyonVoiceEngine.is_japanese_text("")


class TestSubtitleCuesAndRomanization:
    """Verify dual-layer Japanese subtitle cues and romanized voice callouts."""

    def test_subtitle_cue_format(self) -> None:
        cue_jp, cue_rom = TachyonVoiceEngine.get_subtitle_cue("Code refactoring", mood="flow")
        assert isinstance(cue_jp, str)
        assert isinstance(cue_rom, str)
        assert len(cue_jp) > 0
        assert len(cue_rom) > 0
        assert "「" in cue_jp and "」" in cue_jp

    def test_all_moods_have_valid_cues(self) -> None:
        moods = ["flow", "happy", "thinking", "shocked", "serious", "tired"]
        for mood in moods:
            cue_jp, cue_rom = TachyonVoiceEngine.get_subtitle_cue("Sample enterprise message", mood=mood)
            assert TachyonVoiceEngine.is_japanese_text(cue_jp)
            assert not TachyonVoiceEngine.is_japanese_text(cue_rom)


class TestSynthesizeVoicePromptContract:
    """Verify interface contract compliance of synthesize_voice_prompt."""

    def test_contract_keys_and_types(self) -> None:
        res = TachyonVoiceEngine.synthesize_voice_prompt(
            text="High throughput speed test",
            mood="flow",
        )
        assert isinstance(res, dict)
        # Required core keys from PROJECT.md
        assert "japanese_speech_text" in res
        assert "voice" in res
        assert "speed" in res
        assert "subtitle_cue" in res
        assert "mood" in res

        # Types
        assert isinstance(res["japanese_speech_text"], str)
        assert isinstance(res["voice"], str)
        assert isinstance(res["speed"], float)
        assert isinstance(res["subtitle_cue"], str)
        assert isinstance(res["mood"], str)

        # Extended rich keys
        assert "pitch_semitones" in res
        assert "formant_shift" in res
        assert "pause_scale" in res
        assert "voice_mix" in res
        assert "romanized_callout" in res
        assert "cadence_profile" in res
        assert "english_text" in res
        assert res["english_text"] == "High throughput speed test"

    def test_instance_and_class_invocation(self) -> None:
        # Class call
        c_res = TachyonVoiceEngine.synthesize_voice_prompt("Test text", "serious")
        # Instance call
        engine = TachyonVoiceEngine()
        i_res = engine.synthesize_voice_prompt("Test text", "serious")

        assert c_res["mood"] == i_res["mood"] == "serious"
        assert c_res["speed"] == i_res["speed"]
        assert c_res["voice"] == i_res["voice"]

    def test_acoustic_parameters_helper(self) -> None:
        params = TachyonVoiceEngine.get_acoustic_parameters("tired")
        assert params["speed"] < 0.90
        assert params["pitch_semitones"] < -1.0
        assert params["pause_scale"] > 1.2
        assert "voice_mix" in params

    def test_kwargs_parameter_overrides(self) -> None:
        res = TachyonVoiceEngine.synthesize_voice_prompt(
            text="Overriding speed test",
            mood="flow",
            speed=1.50,
            voice="custom_voice",
        )
        assert res["speed"] == 1.50
        assert res["voice"] == "custom_voice"

    def test_edge_cases_empty_and_special_characters(self) -> None:
        # Empty string
        res_empty = TachyonVoiceEngine.synthesize_voice_prompt("", mood="thinking")
        assert res_empty["japanese_speech_text"] != ""
        assert res_empty["mood"] == "thinking"

        # Whitespace
        res_ws = TachyonVoiceEngine.synthesize_voice_prompt("   \n\t   ", mood="happy")
        assert res_ws["japanese_speech_text"] != ""

        # Special symbols, numbers, punctuation
        symbols_text = "### Error 404: NullPointerException @ 0x7FFF8000!?"
        res_sym = TachyonVoiceEngine.synthesize_voice_prompt(symbols_text, mood="shocked")
        assert res_sym["mood"] == "shocked"
        assert TachyonVoiceEngine.is_japanese_text(res_sym["japanese_speech_text"])

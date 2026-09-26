"""Agnes Tachyon Japanese Personality, Catchphrases & Mood Mapping Engine.

This service transforms dialogue into authentic Dr. Agnes Tachyon Japanese voice prompts,
character intonations, and acoustic cadence profiles for Kokoro TTS / Featherless synthesis.
"""
from __future__ import annotations

import re
from typing import Any

from app.data.tachyon_catchphrases import (
    CANONICAL_DIALOGUES,
    MOOD_ACOUSTIC_PROFILES,
    SIGNATURE_CATCHPHRASES,
    THEMATIC_TERMS_MAP,
    MoodAcousticProfile,
    normalize_mood_name,
)


class TachyonVoiceEngine:
    """Engine for transforming dialogue into Agnes Tachyon's authentic Japanese voice persona.

    Provides mood-to-acoustic mapping, mad scientist catchphrase injection,
    and localized dual-layer subtitle cues paired with English enterprise text.
    """

    @classmethod
    def is_japanese_text(cls, text: str) -> bool:
        """Check if text contains Japanese Hiragana, Katakana, or Kanji."""
        if not text:
            return False
        return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text))

    @classmethod
    def normalize_mood(cls, mood: str | Any) -> str:
        """Normalize mood or pose string/enum to one of the 6 canonical moods."""
        return normalize_mood_name(mood)

    @classmethod
    def get_mood_profile(cls, mood: str | Any = "thinking") -> MoodAcousticProfile:
        """Get the acoustic cadence profile and vocal parameters for a mood."""
        norm_mood = cls.normalize_mood(mood)
        return MOOD_ACOUSTIC_PROFILES.get(norm_mood, MOOD_ACOUSTIC_PROFILES["thinking"])

    @classmethod
    def get_acoustic_parameters(cls, mood: str | Any = "thinking") -> dict[str, Any]:
        """Return Kokoro/Featherless TTS acoustic parameters for a given mood."""
        profile = cls.get_mood_profile(mood)
        return {
            "voice": profile.voice,
            "speed": profile.speed,
            "pitch_semitones": profile.pitch_semitones,
            "formant_shift": profile.formant_shift,
            "pause_scale": profile.pause_scale,
            "voice_mix": dict(profile.voice_mix),
            "cadence_profile": profile.cadence_profile,
        }

    @classmethod
    def get_all_catchphrases(cls) -> list[str]:
        """Return a list of Dr. Agnes Tachyon's signature Japanese catchphrases."""
        return list(SIGNATURE_CATCHPHRASES)

    @classmethod
    def get_subtitle_cue(cls, text: str = "", mood: str | Any = "thinking") -> tuple[str, str]:
        """Select an authentic Japanese subtitle cue and romanized voice callout.

        Returns:
            Tuple of (subtitle_cue_jp, romanized_cue_en)
        """
        norm_mood = cls.normalize_mood(mood)
        profile = cls.get_mood_profile(norm_mood)

        # 1. Check if text matches canonical line with predefined cue
        text_lower = (text or "").lower()
        for item in CANONICAL_DIALOGUES:
            for pattern in item["patterns"]:
                if pattern in text_lower:
                    return item["subtitle_cue"], item["romanized_cue"]

        # 2. Select from mood profile cues deterministically based on text length/hash
        cues_jp = profile.subtitle_cues
        cues_rom = profile.romanized_cues
        if cues_jp and cues_rom:
            idx = abs(hash(text_lower)) % len(cues_jp) if text_lower else 0
            return cues_jp[idx], cues_rom[idx]

        return "「ふふっ、我がモルモット君！」", "Fufu, waga Morumotto-kun!"

    @classmethod
    def transform_dialogue_to_japanese(
        cls,
        text: str,
        mood: str | Any = "thinking",
    ) -> str:
        """Convert or transform input text into authentic Agnes Tachyon Japanese anime dialogue.

        Maintains her eccentric, mad scientist intonation, theatrical mannerisms,
        and terms like '我がモルモット君', 'ククク…', '私の光彩が見えるかい？', etc.
        """
        cleaned_text = (text or "").strip()
        norm_mood = cls.normalize_mood(mood)
        profile = cls.get_mood_profile(norm_mood)

        # If empty text, return default characteristic greeting for mood
        if not cleaned_text:
            return f"{profile.prefixes[0]} {profile.suffixes[0]}"

        # If already predominantly Japanese text, preserve it while ensuring Tachyon flair
        if cls.is_japanese_text(cleaned_text):
            has_quirk = any(
                quirk in cleaned_text
                for quirk in ["モルモット", "ククク", "アッハハ", "実験", "光彩", "ふふ", "ほぉ"]
            )
            if has_quirk:
                return cleaned_text
            # Enhance with signature prefix
            prefix = profile.prefixes[0] if profile.prefixes else "ククク…"
            return f"{prefix} {cleaned_text}"

        # Check fast canonical line dictionary
        text_lower = cleaned_text.lower()
        for item in CANONICAL_DIALOGUES:
            for pattern in item["patterns"]:
                if pattern in text_lower:
                    return item["japanese_speech_text"]

        # Assemble eccentric mad scientist speech tailored to detected themes and mood
        prefix = profile.prefixes[abs(hash(cleaned_text)) % len(profile.prefixes)]
        suffix = profile.suffixes[abs(hash(cleaned_text)) % len(profile.suffixes)]

        # Extract matching thematic terms
        matched_terms: list[str] = []
        for word, jp_term in THEMATIC_TERMS_MAP.items():
            if word in text_lower:
                matched_terms.append(jp_term)

        # Synthesize the body
        if matched_terms:
            terms_joined = "と".join(matched_terms[:3])
            if norm_mood == "flow":
                body = f"極限の{terms_joined}が私の光彩と共鳴しているよ！"
            elif norm_mood == "happy":
                body = f"{terms_joined}の観測データは極めて有望だ！"
            elif norm_mood == "shocked":
                body = f"{terms_joined}に想定外の特異点が発生しているぞ！"
            elif norm_mood == "serious":
                body = f"{terms_joined}における厳格な設計原則を遵守したまえ。"
            elif norm_mood == "tired":
                body = f"{terms_joined}の解析で脳細胞が限界だよ…"
            else:
                body = f"{terms_joined}の挙動を深く分析する必要があるねぇ。"
        else:
            if norm_mood == "flow":
                body = "私の理論は限界を突破し、超光速の領域へと達したのだ！"
            elif norm_mood == "happy":
                body = "実証データは完璧、君の働きには大いに満足しているよ！"
            elif norm_mood == "shocked":
                body = "まさか計算結果にこのような致命的矛盾が生じるとはね…！"
            elif norm_mood == "serious":
                body = "規律あるアーキテクチャの構築こそが真理への唯一の道だ。"
            elif norm_mood == "tired":
                body = "今日の実験はここまでだ… 角砂糖をたっぷり入れた紅茶を頼むよ。"
            else:
                body = "我が仮説の正しさをじっくりと検証しようじゃないか。"

        return f"{prefix} {body} {suffix}"

    @classmethod
    def synthesize_voice_prompt(
        cls,
        text: str,
        mood: str | Any = "thinking",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Synthesize Tachyon Japanese speech text, acoustic params, and subtitle cues.

        Interface contract:
        Returns:
            dict with:
                - japanese_speech_text: str (authentic Japanese voice input for TTS)
                - voice: str (Kokoro voice pack e.g. 'jf_nezumi')
                - speed: float (mood-mapped vocal speed)
                - subtitle_cue: str (localized Japanese subtitle header / cue)
                - mood: str (normalized canonical mood)
                - pitch_semitones: float (mood-mapped vocal pitch)
                - formant_shift: float (timbre / resonance adjustment)
                - pause_scale: float (rhythmic spacing / cadence)
                - voice_mix: dict[str, float] (blended voice distribution)
                - romanized_callout: str (phonetic voice callout for English players)
                - cadence_profile: str (descriptive cadence archetype)
                - english_text: str (original input text preserved)
        """
        norm_mood = cls.normalize_mood(mood)
        profile = cls.get_mood_profile(norm_mood)

        japanese_speech_text = cls.transform_dialogue_to_japanese(text=text, mood=norm_mood)
        subtitle_cue, romanized_cue = cls.get_subtitle_cue(text=text, mood=norm_mood)

        # Allow kwargs to optionally override specific acoustic parameters if needed
        speed = float(kwargs.get("speed", profile.speed))
        voice = str(kwargs.get("voice", profile.voice))
        pitch_semitones = float(kwargs.get("pitch_semitones", profile.pitch_semitones))
        formant_shift = float(kwargs.get("formant_shift", profile.formant_shift))
        pause_scale = float(kwargs.get("pause_scale", profile.pause_scale))
        voice_mix = kwargs.get("voice_mix", profile.voice_mix)

        return {
            "japanese_speech_text": japanese_speech_text,
            "voice": voice,
            "speed": speed,
            "subtitle_cue": subtitle_cue,
            "mood": norm_mood,
            "pitch_semitones": pitch_semitones,
            "formant_shift": formant_shift,
            "pause_scale": pause_scale,
            "voice_mix": dict(voice_mix),
            "romanized_callout": romanized_cue,
            "cadence_profile": profile.cadence_profile,
            "english_text": text,
        }

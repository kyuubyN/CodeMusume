"""Agnes Tachyon Japanese Catchphrases, Character Lexicon, and Mood Profiles.

This module houses authentic character dialogue patterns, eccentric mad scientist
speech quirks, acoustic voice parameters, and localized Japanese subtitle cues
for Dr. Agnes Tachyon (Uma Musume: Pretty Derby / CodeMusume Chief Enterprise Architect).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MoodAcousticProfile:
    """Acoustic cadence and synthesis parameters for a character mood."""

    mood: str
    speed: float
    pitch_semitones: float
    formant_shift: float
    pause_scale: float
    voice: str = "jf_nezumi"
    voice_mix: dict[str, float] = field(
        default_factory=lambda: {"jf_nezumi": 0.70, "jf_alpha": 0.30}
    )
    cadence_profile: str = "balanced"
    prefixes: list[str] = field(default_factory=list)
    suffixes: list[str] = field(default_factory=list)
    subtitle_cues: list[str] = field(default_factory=list)
    romanized_cues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mood": self.mood,
            "speed": self.speed,
            "pitch_semitones": self.pitch_semitones,
            "formant_shift": self.formant_shift,
            "pause_scale": self.pause_scale,
            "voice": self.voice,
            "voice_mix": dict(self.voice_mix),
            "cadence_profile": self.cadence_profile,
            "prefixes": list(self.prefixes),
            "suffixes": list(self.suffixes),
            "subtitle_cues": list(self.subtitle_cues),
            "romanized_cues": list(self.romanized_cues),
        }


# ---------------------------------------------------------------------------
# Character Lore & Signature Constants
# ---------------------------------------------------------------------------

TACHYON_NAME_JP = "アグネスタキオン"
TACHYON_NAME_EN = "Dr. Agnes Tachyon"
TACHYON_TITLE_JP = "チーフ・エンタープライズ・アーキテクト"
TACHYON_TITLE_EN = "Chief Enterprise Architect"

TRAINER_TERMS_JP = [
    "我がモルモット君",
    "モルモット君",
    "助手君",
    "君",
]

SIGNATURE_CATCHPHRASES = [
    "我がモルモット君！",
    "興味深いねぇ...",
    "アッハハハ！",
    "実験開始だ！",
    "私の光彩が見えるかい？",
    "ククク…",
    "限界のその先、光の果てを見せてあげるよ。",
    "プランBへ即座に移行したまえ！",
    "角砂糖入りの紅茶でも淹れてくれたまえ...",
]


# ---------------------------------------------------------------------------
# Distinct Mood & Pose Acoustic Profiles
# ---------------------------------------------------------------------------

MOOD_ACOUSTIC_PROFILES: dict[str, MoodAcousticProfile] = {
    "flow": MoodAcousticProfile(
        mood="flow",
        speed=1.16,
        pitch_semitones=1.2,
        formant_shift=0.1,
        pause_scale=0.75,
        voice="jf_nezumi",
        voice_mix={"jf_nezumi": 0.75, "jf_alpha": 0.25},
        cadence_profile="frenzied_brilliance",
        prefixes=[
            "アッハハハ！見ろ、我がモルモット君！",
            "私の光彩が見えるかい？",
            "ククク… 限界のその先、光の果てが見えてきたよ！",
            "素晴らしい！理論値を超える加速だ！",
            "ゾーンに入ったよ… 全てのコードが光り輝いている！",
        ],
        suffixes=[
            "限界のその先へ、共に行こうじゃないか！",
            "これぞ真の超光速アーキテクチャだよ！",
            "私の光彩に焼き尽くされないようにねぇ！",
            "アッハハハ！実験は大成功だ！",
        ],
        subtitle_cues=[
            "「アッハハハ！私の光彩が見えるかい？」",
            "「見ろ、限界のその先だ！」",
            "「ククク… 光の果てへ行こう！」",
            "「我がモルモット君、ゾーン突入だよ！」",
        ],
        romanized_cues=[
            "Ahhahaha! Watashi no kousai ga mieru kai?",
            "Miro, genkai no sono saki da!",
            "Kukuku... Hikari no hate he ikou!",
            "Waga Morumotto-kun, zoon totsunyuu da yo!",
        ],
    ),
    "happy": MoodAcousticProfile(
        mood="happy",
        speed=1.08,
        pitch_semitones=0.5,
        formant_shift=0.0,
        pause_scale=0.85,
        voice="jf_nezumi",
        voice_mix={"jf_nezumi": 0.70, "jf_alpha": 0.30},
        cadence_profile="buoyant_amusement",
        prefixes=[
            "ククク… ご機嫌だねぇ、モルモット君！",
            "ふふっ、実に興味深く、喜ばしい結果だ。",
            "我がモルモット君！君の成長は私の観測対象として最高だよ！",
            "おや、実に素晴らしい成果じゃないか。",
            "ハハッ、これだから君の実験体としての価値は計り知れないねぇ！",
        ],
        suffixes=[
            "実に良いデータが採れたよ、感謝するよ！",
            "次の実験が今から待ちきれないねぇ！",
            "この調子で我が理論を加速させたまえ！",
            "ククク… ご褒美に特製の薬品…いや、紅茶でも淹れようか？",
        ],
        subtitle_cues=[
            "「ククク… 素晴らしいじゃないか、モルモット君！」",
            "「ふふっ、実に喜ばしい結果だよ。」",
            "「我がモルモット君！最高峰の実験だ！」",
            "「ハハッ、実に良いデータだねぇ！」",
        ],
        romanized_cues=[
            "Kukuku... Subarashii ja nai ka, Morumotto-kun!",
            "Fufu, jitsuni yorokobashii kekka da yo.",
            "Waga Morumotto-kun! Saikouhou no jikken da!",
            "Haha, jitsuni yoi deeta da nee!",
        ],
    ),
    "thinking": MoodAcousticProfile(
        mood="thinking",
        speed=0.96,
        pitch_semitones=-0.3,
        formant_shift=-0.1,
        pause_scale=1.15,
        voice="jf_nezumi",
        voice_mix={"jf_nezumi": 0.70, "jf_alpha": 0.30},
        cadence_profile="deliberate_inquiry",
        prefixes=[
            "ほぉ… 興味深いねぇ...",
            "ふむ… 我がモルモット君、この変数をどう見るかい？",
            "奇妙だな… 理論式と微小な乖離があるようだ。",
            "おやおや… 観測データに未知の揺らぎが検出されたよ。",
            "じっくりと観察させてもらおうか…",
        ],
        suffixes=[
            "…更なる検証が必要不可欠だねぇ。",
            "…仮説を再構築して、追加実験を行おう。",
            "…君の意見も聞かせてくれたまえ、助手君。",
            "…ふふ、謎が深まるほど知的好奇心が刺激されるよ。",
        ],
        subtitle_cues=[
            "「ほぉ… 興味深いねぇ...」",
            "「ふむ… 我がモルモット君、仮説を検証しよう。」",
            "「おやおや… 奇妙な揺らぎだねぇ。」",
            "「じっくりと観察させてもらおうか。」",
        ],
        romanized_cues=[
            "Hoo... Kyoumibukai nee...",
            "Fumu... Waga Morumotto-kun, kasetsu wo kenshou shiyou.",
            "Oya oya... Kimyou na yuragi da nee.",
            "Jikkuri to kansatsu sasete moraou ka.",
        ],
    ),
    "shocked": MoodAcousticProfile(
        mood="shocked",
        speed=1.16,
        pitch_semitones=2.0,
        formant_shift=0.3,
        pause_scale=0.70,
        voice="jf_nezumi",
        voice_mix={"jf_nezumi": 0.65, "jf_alpha": 0.35},
        cadence_profile="agitated_disbelief",
        prefixes=[
            "な、何だって…！？",
            "おやおや… 予想外の特異点が発生したよ！",
            "馬鹿な… 計算が狂ったというのか！？",
            "異常事態発生だ、モルモット君！",
            "あり得ない… この私が計算ミスを犯したとでも言うのかい！？",
        ],
        suffixes=[
            "直ちにプランBへ移行したまえ！",
            "データの破損を食い止めるんだ！急ぎたまえ！",
            "だが… この破滅的なデータもまた、魅惑的だねぇ…！",
            "急ぎリカバリープロトコルを実行するよ！",
        ],
        subtitle_cues=[
            "「な、何だって…！？ 予想外の特異点だよ！」",
            "「計算が…狂ったというのか！？」",
            "「直ちにプランBへ移行したまえ！」",
            "「異常事態だ、急ぎたまえモルモット君！」",
        ],
        romanized_cues=[
            "Na, nan datte...!? Yosougai no tokuiten da yo!",
            "Keisan ga... kurutta to iu no ka!?",
            "Tadachini puran B he ikou shitamae!",
            "Ijoutai da, isogitamae Morumotto-kun!",
        ],
    ),
    "serious": MoodAcousticProfile(
        mood="serious",
        speed=1.00,
        pitch_semitones=-0.9,
        formant_shift=-0.2,
        pause_scale=1.00,
        voice="jf_nezumi",
        voice_mix={"jf_nezumi": 0.80, "jf_alpha": 0.20},
        cadence_profile="commanding_rigor",
        prefixes=[
            "実験開始だ！刮目したまえ、我がモルモット君。",
            "我がモルモット君、ここからは真剣な話だよ。",
            "チーフ・エンタープライズ・アーキテクトとして告げる。",
            "妥協なき設計こそが、システムの命運を分けるのだ。",
            "無駄口はここまでだ。厳格なプロトコルに従いたまえ。",
        ],
        suffixes=[
            "我が理論に一切の曖昧さは不要さ。",
            "規律あるアーキテクチャこそが真理を導くのだ。",
            "失敗は許されない。完璧な実証を期待しているよ。",
            "君の全能力を以て、この命題に応えたまえ。",
        ],
        subtitle_cues=[
            "「実験開始だ！ 刮目したまえ、我がモルモット君。」",
            "「妥協なき設計こそがシステムの命運を分ける。」",
            "「我が理論に一切の曖昧さは不要さ。」",
            "「厳格なプロトコルに従いたまえ。」",
        ],
        romanized_cues=[
            "Jikken kaishi da! Katsumoku shitamae, waga Morumotto-kun.",
            "Dakyounaki sekkei koso ga shisutemu no meiun wo wakeru.",
            "Waga riron ni issai no aimaisa wa fuyou sa.",
            "Genkaku na purotokoru ni shitagaitamae.",
        ],
    ),
    "tired": MoodAcousticProfile(
        mood="tired",
        speed=0.86,
        pitch_semitones=-1.8,
        formant_shift=-0.3,
        pause_scale=1.35,
        voice="jf_nezumi",
        voice_mix={"jf_nezumi": 0.60, "jf_alpha": 0.40},
        cadence_profile="languid_exhaustion",
        prefixes=[
            "ふぁぁ… さすがに消耗したねぇ...",
            "やれやれ… 角砂糖とカフェインが決定的に不足しているよ...",
            "もう限界だよ、モルモット君… 頭がオーバーヒートしそうだ…",
            "実験は一時中断さ… 私の生命維持装置が悲鳴を上げている…",
            "紅茶… 熱くて甘い紅茶を頼むよ...",
        ],
        suffixes=[
            "…紅茶でも淹れてくれたまえ、モルモット君…",
            "…少し研究室のソファで横にならせてもらうよ…",
            "…メンテナンスもまた、アーキテクトの義務さ…",
            "…君の肩を借りてもいいかい…？ ふぁぁ…",
        ],
        subtitle_cues=[
            "「ふぁぁ… 紅茶でも淹れてくれたまえ、モルモット君…」",
            "「角砂糖とカフェインが決定的に不足しているよ…」",
            "「少しソファで横にならせてもらうよ…」",
            "「やれやれ… オーバーヒートしそうだ…」",
        ],
        romanized_cues=[
            "Fwaaa... Koucha demo irete kuretamae, Morumotto-kun...",
            "Kakuzatou to kafein ga ketteiteki ni fusoku shite iru yo...",
            "Sukoshi sofa de yoko ni narasete morau yo...",
            "Yareyare... oobaahiito shisou da...",
        ],
    ),
}


# ---------------------------------------------------------------------------
# Canonical Pre-Mapped Dialogue Repository
# ---------------------------------------------------------------------------

CANONICAL_DIALOGUES: list[dict[str, Any]] = [
    {
        "patterns": ["greetings, morumotto-kun", "chief enterprise architect", "grand software experiment"],
        "default_mood": "serious",
        "japanese_speech_text": "ククク… ごきげんよう、我がモルモット君！ 私は君のチーフ・エンタープライズ・アーキテクト、アグネスタキオン博士だ。最高峰のソフトウェア実験を始めようじゃないか！",
        "subtitle_cue": "「ククク… ごきげんよう、我がモルモット君！」",
        "romanized_cue": "Kukuku... Gokigenyou, waga Morumotto-kun!",
    },
    {
        "patterns": ["rest is not laziness", "recovery time", "take a rest"],
        "default_mood": "tired",
        "japanese_speech_text": "ふぁぁ… 休息もまた実験の重要な過程さ。角砂糖入りの紅茶でも淹れてくれたまえ、モルモット君。",
        "subtitle_cue": "「ふぁぁ… 紅茶でも淹れてくれたまえ、モルモット君…」",
        "romanized_cue": "Fwaaa... Koucha demo irete kuretamae, Morumotto-kun...",
    },
    {
        "patterns": ["catastrophic metabolic failure", "experiment collapsed", "training failure", "production incident"],
        "default_mood": "shocked",
        "japanese_speech_text": "な、何だって…！？ 失敗も実験の醍醐味だが… 想定外の特異点だよ。直ちにプランBへ移行したまえ、モルモット君！",
        "subtitle_cue": "「な、何だって…！？ 直ちにプランBだ、モルモット君！」",
        "romanized_cue": "Na, nan datte...!? Tadachini puran B da, Morumotto-kun!",
    },
    {
        "patterns": ["synthesized the cure", "grand derby victory", "ultimate breakthrough"],
        "default_mood": "flow",
        "japanese_speech_text": "アッハハハ！見事だ、我がモルモット君！ 私の光彩が見えるかい？ 我々のアーキテクチャが限界の先へ到達したよ！",
        "subtitle_cue": "「アッハハハ！私の光彩が見えるかい？」",
        "romanized_cue": "Ahhahaha! Watashi no kousai ga mieru kai?",
    },
]


# ---------------------------------------------------------------------------
# Thematic Keyword Vocabulary (Enterprise + Mad Scientist)
# ---------------------------------------------------------------------------

THEMATIC_TERMS_MAP: dict[str, str] = {
    "architecture": "基本設計アーキテクチャ",
    "architect": "アーキテクト",
    "refactor": "リファクタリング",
    "pattern": "設計パターン",
    "database": "データベース機構",
    "cache": "キャッシュ機構",
    "speed": "超光速スループット",
    "stamina": "高負荷持続性",
    "power": "推進演算能力",
    "guts": "耐障害性ガッツ",
    "wisdom": "アーキテクチャ叡智",
    "test": "実証検証プロトコル",
    "scan": "構文木スキャン",
    "ast": "抽象構文木",
    "bug": "特異点バグ",
    "error": "例外エラー",
    "exception": "異常例外",
    "crash": "システム破綻",
    "memory": "メモリリソース",
    "cpu": "演算コア",
    "experiment": "科学実験",
    "hypothesis": "作業仮説",
    "data": "観測データ",
    "morumotto": "モルモット君",
    "trainer": "モルモット君",
}


def normalize_mood_name(mood: str | Any) -> str:
    """Normalize any mood or pose string/enum to one of the 6 canonical moods."""
    if hasattr(mood, "value"):
        mood_str = str(mood.value).lower().strip()
    else:
        mood_str = str(mood or "").lower().strip()

    # Direct canonical matches
    if mood_str in MOOD_ACOUSTIC_PROFILES:
        return mood_str

    # Pose & Mood aliases mapping
    alias_map = {
        "idle": "thinking",
        "great": "flow",
        "good": "happy",
        "normal": "thinking",
        "poor": "serious",
        "terrible": "tired",
        "ecstatic": "flow",
        "excited": "flow",
        "joy": "happy",
        "pleased": "happy",
        "delight": "happy",
        "curious": "thinking",
        "analyzing": "thinking",
        "pondering": "thinking",
        "investigating": "thinking",
        "alarmed": "shocked",
        "panic": "shocked",
        "surprise": "shocked",
        "surprised": "shocked",
        "strict": "serious",
        "focused": "serious",
        "discipline": "serious",
        "exhausted": "tired",
        "sleepy": "tired",
        "rest": "tired",
        "drain": "tired",
    }

    return alias_map.get(mood_str, "thinking")

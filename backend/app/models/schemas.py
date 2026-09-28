from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AttributeType(str, Enum):
    SPEED = "speed"
    STAMINA = "stamina"
    POWER = "power"
    GUTS = "guts"
    WISDOM = "wisdom"


class StatRank(str, Enum):
    G = "G"
    F = "F"
    E = "E"
    D = "D"
    C = "C"
    B = "B"
    A = "A"
    S = "S"
    SS = "SS"


def score_to_rank(score: int) -> StatRank:
    """Convert a numeric score to its corresponding StatRank."""
    if score >= 1150:
        return StatRank.SS
    if score >= 1000:
        return StatRank.S
    if score >= 800:
        return StatRank.A
    if score >= 700:
        return StatRank.B
    if score >= 600:
        return StatRank.C
    if score >= 500:
        return StatRank.D
    if score >= 400:
        return StatRank.E
    if score >= 200:
        return StatRank.F
    return StatRank.G


class MoodState(str, Enum):
    """Agnes Tachyon's current mood.

    絶不調 (-20% exp) / 不調 (-10% exp) / 普通 (0%) / 好調 (+10% exp) / 絶好調 (+20% exp)
    """
    TERRIBLE = "terrible"  # 絶不調, -20% exp
    POOR = "poor"           # 不調,   -10% exp
    NORMAL = "normal"       # 普通,     0%
    GOOD = "good"           # 好調,   +10% exp
    GREAT = "great"         # 絶好調, +20% exp


class AvatarPose(str, Enum):
    idle = "idle"
    thinking = "thinking"
    shocked = "shocked"
    happy = "happy"
    serious = "serious"
    tired = "tired"
    flow = "flow"
    crazy = "crazy"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AttributeScores(BaseModel):
    speed: int = 200
    stamina: int = 200
    power: int = 200
    guts: int = 200
    wisdom: int = 200

    def get_ranks(self) -> dict[str, StatRank]:
        """Return the StatRank for each attribute."""
        return {
            "speed": score_to_rank(self.speed),
            "stamina": score_to_rank(self.stamina),
            "power": score_to_rank(self.power),
            "guts": score_to_rank(self.guts),
            "wisdom": score_to_rank(self.wisdom),
        }


DEFAULT_INITIAL_DIALOGUE = (
    "Kukuku… Greetings, Morumotto-kun! I am Dr. Agnes Tachyon, your Chief Enterprise Architect. "
    "I will guide you through strict enterprise architecture and industry best practices. "
    "Let our grand software experiment commence!"
)


class GameState(BaseModel):
    mode: str = "repo"                      # "lab" (career on the specimen) | "repo" (free lab on your code)
    repo_name: str = "code-musume"
    turn: int = 1
    max_turns: int = 12
    energy: int = Field(default=100, ge=0, le=100)
    mood: MoodState = MoodState.NORMAL
    attributes: AttributeScores = Field(default_factory=AttributeScores)
    current_pose: AvatarPose = AvatarPose.idle
    dialogue: str = ""
    is_game_over: bool = False
    interactions_in_cycle: int = 0
    interactions_required: int = 3
    race_unlocked: bool = False
    learned_insights: list[str] = Field(default_factory=list)


class CodeSmell(BaseModel):
    """A real finding from the AST scanner, tracked across rescans by a stable key."""
    id: int
    key: str
    attribute: AttributeType
    rule_id: str
    file_path: str
    line_number: int
    description: str
    tachyon_critique: str
    suggested_fix: str
    code_snippet: str
    drilled: bool = False


class TrainRequest(BaseModel):
    attribute: AttributeType
    custom_knowledge: str | None = None


class TrainResult(BaseModel):
    success: bool
    attribute: AttributeType
    stat_gained: int
    energy_spent: int
    failure_rate: float
    tachyon_commentary: str
    pose: AvatarPose
    updated_state: GameState
    mcp_insight: str | None = None
    smell: CodeSmell | None = None


class RestResult(BaseModel):
    energy_recovered: int
    new_mood: MoodState
    tachyon_commentary: str
    updated_state: GameState


class RaceRival(BaseModel):
    id: str
    name: str
    architecture_style: str
    attributes: AttributeScores
    current_distance: float = 0.0
    status: str = "running"


class RaceIncident(BaseModel):
    sector: int
    distance_m: float
    name: str
    tested_attribute: AttributeType
    description: str
    player_success: bool
    tachyon_callout: str


class RaceTick(BaseModel):
    tick: int                                   # 0 to 100
    distance_m: float                           # 0 to 2000.0
    player_distance: float
    rivals: list[RaceRival]
    active_incident: RaceIncident | None = None
    commentary: str | None = None
    is_finished: bool = False


# ---------------------------------------------------------------------------
# Architecture Exam & Qualification Models
# ---------------------------------------------------------------------------

class QuizQuestion(BaseModel):
    id: str
    question: str
    options: list[str]
    tested_attribute: AttributeType = AttributeType.WISDOM
    context_hint: str | None = None


class QuizEvaluationRequest(BaseModel):
    question_id: str
    selected_index: int


class QuizEvaluationResponse(BaseModel):
    correct: bool
    correct_index: int
    explanation: str
    speed_delta: float = 3.0


class RaceCompleteRequest(BaseModel):
    place: int = 1
    points_awarded: int = 0



class RescanResult(BaseModel):
    """Outcome of re-scanning the repository after the trainer edited real code."""
    fixed: list[CodeSmell]
    new: list[CodeSmell]
    remaining: int
    attribute_deltas: dict[str, int]
    updated_state: GameState

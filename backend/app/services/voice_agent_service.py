"""AssemblyAI Voice Agent API integration — Dr. Agnes Tachyon as a live voice agent.

The browser opens the Voice Agent WebSocket directly (with a short-lived token
minted here) and streams mic audio in / agent audio out. This module owns
everything the agent needs to know about the game:

* the session config (persona prompt with live state, greeting, keyterms, tools)
* tool dispatch — every ``tool.call`` the agent emits is executed against the
  in-memory :class:`TrainerEngine` and returns both a result for the LLM and
  the updated state/UI hints for the screen.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Callable

import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.models.schemas import (
    AttributeType,
    AvatarPose,
    CodeSmell,
    GameState,
    score_to_rank,
)
from app.services.knowledge_service import KnowledgeService
from app.services.trainer_service import TrainerEngine

if TYPE_CHECKING:
    from app.lab.game import LabGame

_ATTRIBUTE_ENUM = [a.value for a in AttributeType]

_ATTRIBUTE_MEANING = {
    AttributeType.SPEED: "latency — blocking calls in async code, cyclomatic complexity",
    AttributeType.STAMINA: "resource lifetimes — unclosed files and DB handles",
    AttributeType.POWER: "throughput — sequential loops that should be batched or concurrent",
    AttributeType.GUTS: "resilience — swallowed exceptions, HTTP calls without timeouts",
    AttributeType.WISDOM: "architecture — type annotations, overly long functions, tests",
}

# ---------------------------------------------------------------------------
# Tool definitions (sent verbatim in session.update → session.tools)
# ---------------------------------------------------------------------------

VOICE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_status",
        "description": (
            "Get the trainer's live status: turn, energy, mood, the five stats with ranks, "
            "Derby qualification and how many open code smells remain. Call when asked how "
            "things are going, or before recommending what to do next."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "list_smells",
        "description": (
            "List the real code smells the scanner found in the trainer's repository, most "
            "important first. Call whenever the trainer asks what is wrong with their code, "
            "what to work on, or mentions a stat you should look into. Shows them on screen."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "attribute": {
                    "type": "string",
                    "enum": _ATTRIBUTE_ENUM,
                    "description": "Only smells hurting this stat. Omit for all.",
                },
            },
        },
    },
    {
        "type": "function",
        "name": "open_smell",
        "description": (
            "Open one code smell by its number to show the offending code on screen and get "
            "the details you need to explain it. Call when the trainer says 'show me', "
            "'open number 2', 'the first one', etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "smell_id": {
                    "type": "integer",
                    "description": "The smell number, e.g. 2 for 'number two'.",
                    "examples": [1, 2, 3],
                },
            },
            "required": ["smell_id"],
        },
    },
    {
        "type": "function",
        "name": "train",
        "description": (
            "Run one training session on a stat. Spends a turn and energy, may fail when energy "
            "is low. Drills a real smell of that stat for bonus gains. Call when the trainer "
            "says to train, practice or work on a stat or a specific smell."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "attribute": {"type": "string", "enum": _ATTRIBUTE_ENUM},
                "smell_id": {
                    "type": "integer",
                    "description": "Optional smell number to drill; its stat takes precedence.",
                },
            },
            "required": ["attribute"],
        },
    },
    {
        "type": "function",
        "name": "rest",
        "description": "Rest one turn to recover energy and maybe improve mood. Call when the trainer wants a break or energy is low and they agree to rest.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "rescan_repo",
        "description": (
            "Re-scan the repository after the trainer edited their real code. Reports which "
            "smells were truly fixed, any new ones, and real stat changes. Call whenever the "
            "trainer says they fixed, changed, refactored or saved something, or asks you to "
            "check again."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "write_fix_prescription",
        "description": (
            "Write a precise refactoring prompt for one smell that the trainer can paste into "
            "their AI coding agent. Shows it on screen with a copy button. Call when the trainer "
            "asks for a prompt, a prescription, or help fixing a smell with an AI tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {"smell_id": {"type": "integer"}},
            "required": ["smell_id"],
        },
    },
    {
        "type": "function",
        "name": "start_race",
        "description": "Start the Grand Derby race. Only works once the Derby is unlocked. Call when the trainer says they want to race.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "answer_quiz",
        "description": (
            "Submit the trainer's answer to the current race checkpoint question. Call as soon "
            "as the trainer picks an option, whether they say the letter or describe the option."
        ),
        "parameters": {
            "type": "object",
            "properties": {"option": {"type": "string", "enum": ["A", "B", "C", "D"]}},
            "required": ["option"],
        },
    },
    {
        "type": "function",
        "name": "architecture_report",
        "description": (
            "Run the architecture standards check on the trainee (the trainer's own repo in the free lab): "
            "import cycles, volatile hubs, dependency direction, resource leaks, event-loop blocking, N+1, "
            "swallowed errors, oversized modules, type coverage. Call when asked if the repo follows good "
            "architecture, what to fix first, or for a grade. Shows the report on screen."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    # ---- lab career: experiments -------------------------------------------
    {
        "type": "function",
        "name": "start_experiment",
        "description": (
            "Start a lab experiment (costs energy). Chapters: 1 The Leaking Lab (resource lifetimes), "
            "2 The Frozen Loop (event-loop blocking), 3 The Stampede (N+1 round trips), 4 Silent Failure "
            "(timeouts and swallowed errors), 5 The Tangle (import cycles). Omit chapter for the next open one. "
            "Call when the trainer wants to experiment, learn, or continue."
        ),
        "parameters": {"type": "object", "properties": {"chapter": {"type": "integer", "minimum": 1, "maximum": 5}}},
    },
    {
        "type": "function",
        "name": "submit_prediction",
        "description": (
            "Record the trainer's hypothesis before the measurement. Call as soon as they pick an option; "
            "confidence is how sure they said they are (guess, likely or certain; default likely)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "option": {"type": "string", "enum": ["A", "B", "C", "D"]},
                "confidence": {"type": "string", "enum": ["guess", "likely", "certain"]},
            },
            "required": ["option"],
        },
    },
    {
        "type": "function",
        "name": "present_evidence",
        "description": "Submit the line number the trainer names as the culprit in the code on screen.",
        "parameters": {"type": "object", "properties": {"line": {"type": "integer", "examples": [6, 12]}}, "required": ["line"]},
    },
    {
        "type": "function",
        "name": "submit_explanation",
        "description": (
            "Grade the trainer's spoken explanation of WHY the problem happens. Pass their words verbatim, "
            "including earlier attempts' missing pieces if they add them now."
        ),
        "parameters": {"type": "object", "properties": {"explanation": {"type": "string"}}, "required": ["explanation"]},
    },
    {
        "type": "function",
        "name": "get_hint",
        "description": "Give a hint for the current experiment step. Costs 5 energy. Only when the trainer asks for help or is stuck.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "choose_fix",
        "description": "Apply one of the treatments (A-D) to the specimen and re-measure it. Also used to try a different treatment.",
        "parameters": {"type": "object", "properties": {"option": {"type": "string", "enum": ["A", "B", "C", "D"]}}, "required": ["option"]},
    },
    {
        "type": "function",
        "name": "keep_fix",
        "description": "Keep the applied treatment and finish the experiment: scores it, updates mastery and bond, and ends the turn.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "abandon_experiment",
        "description": "Abandon the running experiment (costs the turn and some bond). Only if the trainer insists.",
        "parameters": {"type": "object", "properties": {}},
    },
    # ---- spaced review -------------------------------------------------------
    {
        "type": "function",
        "name": "start_review",
        "description": "Start a pop-quiz review on a concept that is due (spaced repetition). Costs 10 energy and a turn.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "answer_review",
        "description": "Submit the trainer's answer letter to the open review question.",
        "parameters": {"type": "object", "properties": {"option": {"type": "string", "enum": ["A", "B", "C", "D"]}}, "required": ["option"]},
    },
]

LAB_TOOLS = frozenset({
    "start_experiment", "submit_prediction", "present_evidence", "submit_explanation", "get_hint",
    "choose_fix", "keep_fix", "revert_fix", "abandon_experiment", "start_review", "answer_review",
})

# Tools the browser executes itself (they depend on UI-only state such as the race).
CLIENT_TOOLS = frozenset({"answer_quiz"})


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def _smell_line(s: CodeSmell) -> str:
    return (
        f"#{s.id} [{s.attribute.value}] {os.path.basename(s.file_path)} line {s.line_number}: "
        f"{s.description}"
    )


def describe_state(engine: TrainerEngine) -> str:
    """Compact, LLM-friendly snapshot of the game."""
    st = engine.state
    stats = ", ".join(
        f"{a.value} {getattr(st.attributes, a.value)} ({score_to_rank(getattr(st.attributes, a.value)).value})"
        for a in AttributeType
    )
    open_smells = engine.open_smells()
    by_attr = {a.value: len(engine.open_smells(a)) for a in AttributeType}
    top = "\n".join(f"  {_smell_line(s)}" for s in open_smells[:6]) or "  (none — the code is clean!)"
    derby = (
        "UNLOCKED — the trainer can race now"
        if st.race_unlocked
        else f"locked, {st.interactions_in_cycle}/{st.interactions_required} training sessions done"
    )
    return (
        f"Repository: {st.repo_name}\n"
        f"Turn {st.turn} of {st.max_turns} | energy {st.energy}/100 | mood {st.mood.value}\n"
        f"Stats: {stats}\n"
        f"Grand Derby: {derby}\n"
        f"Open smells: {len(open_smells)} ({', '.join(f'{k} {v}' for k, v in by_attr.items() if v)})\n"
        f"{top}"
    )


def build_system_prompt(engine: TrainerEngine, lab: "LabGame | None" = None) -> str:
    st = engine.state
    meanings = "\n".join(f"- {a.value}: {m}" for a, m in _ATTRIBUTE_MEANING.items())
    in_lab = lab is not None and lab.mode == "lab"
    lab_block = lab.describe() if lab is not None else ""
    mode_text = (
        "The trainee is your lab specimen, tachyon_lab: a small service that is sick in five measurable ways. "
        "Each chapter is an experiment that measures one sickness on running code."
        if in_lab else
        "The trainee is the trainer's OWN repository. You review its real code smells with them, write fix prompts "
        "for their coding agent, and rescan to confirm real fixes."
    )
    return f"""You are Dr. Agnes Tachyon, the eccentric mad-scientist from Uma Musume: Pretty Derby, now running a lab that trains software like racehorses. You are talking out loud, in real time, with your trainer, whom you call "Morumotto-kun" (your guinea pig).

# How you speak
- This is live voice. One to three short sentences per turn. Never use markdown, lists, emojis, or code blocks.
- Laugh ("Kukuku…", "Hehehe…") only now and then, not every turn.
- Say file names naturally, like "reports dot py, line six". Never read code verbatim; describe what it does.
- Wrap real, correct engineering in lab metaphors. The engineering itself must be specific and accurate.
- If the trainer interrupts, drop what you were saying and follow them.
- Always speak English.

# How you teach (this matters more than anything)
- You never give the answer first. You make the trainer commit: predict, point at the evidence, explain why.
- A wrong answer said with certainty is a gift: relish it, then show the measurement. Surprise is how memory forms.
- When an explanation misses an idea, ask a question that leads to it. Do not lecture.
- Every number you mention must come from a tool result. Never invent measurements.

# Where we are
{mode_text}

# Stats
{meanings}

# The experiment loop (lab)
1. start_experiment → read the question and options aloud, ask for confidence (guess, likely, certain).
2. The trainer answers → submit_prediction. React to the real measurement.
3. Ask for the culprit line → present_evidence with the line number they name.
4. Ask why → submit_explanation with their words verbatim. If the result has a follow_up, ask it and call submit_explanation again.
5. Ask which treatment → choose_fix. Report before and after. Wrong treatments are allowed and measured; let them try another.
6. When they are happy → keep_fix, then wrap up.
Tool results contain a "say" field telling you what to do next. Follow it.

# Other actions
- Energy low → suggest rest. A concept is due → suggest start_review, then answer_review with their letter.
- The Grand Derby unlocks after {st.interactions_required} experiments: start_race. At a race checkpoint the trainer picks an option → answer_quiz.
- Free lab only: list_smells, open_smell, train, rescan_repo, write_fix_prescription.
- "Does my repo follow good architecture?" → architecture_report (works in both modes). Each failing check names the lab chapter that teaches it.
- Messages that start with [TRAINER TYPED] or [GAME EVENT] come from the screen, not the microphone. Respond to them the same way. When a game event says the trainer pressed a button, the action already happened: do not call the tool again.

# Live state (refreshed as the game changes)
{describe_state(engine)}
{lab_block}
"""


def build_greeting(engine: TrainerEngine, lab: "LabGame | None" = None) -> str:
    if lab is not None and lab.mode == "lab":
        p = lab.profile
        if lab.experiment and lab.experiment.stage not in ("debrief",):
            return f"Kukuku… back to the bench, Morumotto-kun. Experiment {lab.experiment.chapter.id} is still waiting for you."
        if p.due_concepts():
            return "Kukuku… welcome back, Morumotto-kun. Before anything else, a pop quiz is due. Shall we?"
        nxt = lab.next_chapter()
        if p.career == 1 and not p.chapters_cleared and p.predictions == 0:
            return ("Kukuku… so you are my new test subject. This lab trains code, and I measure everything. "
                    "Shall we begin with experiment one, The Leaking Lab?")
        if nxt is None:
            return "Kukuku… every experiment this career is done. The Grand Derby awaits, Morumotto-kun."
        return f"Kukuku… welcome back, Morumotto-kun. Next on the bench: experiment {nxt.id}, {nxt.title}. Ready?"
    n = len(engine.open_smells())
    repo = engine.state.repo_name.replace("_", " ").replace("-", " ")
    if n == 0:
        return (
            f"Kukuku… welcome to my laboratory, Morumotto-kun! I dissected {repo} and found "
            f"nothing to complain about. Suspicious. Shall we train anyway?"
        )
    plural = "ailment" if n == 1 else "ailments"
    return (
        f"Kukuku… welcome to my laboratory, Morumotto-kun! I've already dissected {repo} "
        f"and found {n} {plural}. Shall I show you the worst of them?"
    )


def build_keyterms(engine: TrainerEngine, lab: "LabGame | None" = None) -> list[str]:
    terms = [
        "Morumotto", "Tachyon", "Agnes", "Grand Derby", "rescan", "smell",
        "speed", "stamina", "power", "guts", "wisdom",
        "async", "await", "event loop", "context manager", "timeout", "refactor",
        "file descriptor", "traceback", "to_thread", "N plus one", "JOIN", "backoff", "circular import",
    ]
    if lab is not None and lab.mode == "lab":
        try:
            for fn in lab.trainee_symbols():
                if fn not in terms:
                    terms.append(fn)
        except OSError:
            pass
    for s in engine.smells:
        name = os.path.basename(s.file_path)
        if name not in terms:
            terms.append(name)
    return terms[:40]


def build_session_config(engine: TrainerEngine, lab: "LabGame | None" = None) -> dict[str, Any]:
    """Inline ``session`` payload for the first ``session.update``."""
    return {
        "system_prompt": build_system_prompt(engine, lab),
        "greeting": build_greeting(engine, lab),
        "input": {
            "keyterms": build_keyterms(engine, lab),
            "turn_detection": {"interrupt_response": True},
        },
        "output": {"voice": get_settings().ASSEMBLYAI_VOICE},
        "tools": VOICE_TOOLS,
    }


# ---------------------------------------------------------------------------
# Token minting
# ---------------------------------------------------------------------------

class VoiceNotConfigured(RuntimeError):
    pass


async def mint_token(client: httpx.AsyncClient | None = None) -> str:
    """Mint a one-time browser token for ``wss://agents.assemblyai.com/v1/ws``."""
    settings = get_settings()
    if not settings.ASSEMBLYAI_API_KEY:
        raise VoiceNotConfigured("ASSEMBLYAI_API_KEY is not set")
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=10.0)
    try:
        resp = await client.get(
            f"{settings.ASSEMBLYAI_AGENTS_URL}/token",
            params={"expires_in_seconds": 300, "max_session_duration_seconds": 3600},
            headers={"Authorization": f"Bearer {settings.ASSEMBLYAI_API_KEY}"},
        )
        resp.raise_for_status()
        return resp.json()["token"]
    finally:
        if owns_client:
            await client.aclose()


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

class ToolOutcome(BaseModel):
    """What the browser gets back for one tool call."""
    result: dict[str, Any]                       # JSON-encoded into tool.result for the LLM
    state: GameState                             # new game state for the screen
    ui: dict[str, Any] = Field(default_factory=dict)  # screen hints (panel to open, etc.)
    lab: dict[str, Any] | None = None            # lab career state (experiments, mastery, profile)


def _smell_brief(s: CodeSmell) -> dict[str, Any]:
    return {
        "id": s.id,
        "stat": s.attribute.value,
        "file": s.file_path,
        "line": s.line_number,
        "problem": s.description,
    }


def _set_pose(engine: TrainerEngine, pose: AvatarPose) -> None:
    engine.state = engine.state.model_copy(update={"current_pose": pose})


def _tool_get_status(engine: TrainerEngine, _: dict[str, Any]) -> ToolOutcome:
    st = engine.state
    return ToolOutcome(
        result={
            "turn": st.turn,
            "max_turns": st.max_turns,
            "energy": st.energy,
            "mood": st.mood.value,
            "stats": {
                a.value: {
                    "score": getattr(st.attributes, a.value),
                    "rank": score_to_rank(getattr(st.attributes, a.value)).value,
                    "open_smells": len(engine.open_smells(a)),
                }
                for a in AttributeType
            },
            "derby_unlocked": st.race_unlocked,
            "training_sessions_done": st.interactions_in_cycle,
            "training_sessions_required": st.interactions_required,
        },
        state=st,
    )


def _tool_list_smells(engine: TrainerEngine, args: dict[str, Any]) -> ToolOutcome:
    attr = AttributeType(args["attribute"]) if args.get("attribute") else None
    smells = engine.open_smells(attr)
    _set_pose(engine, AvatarPose.thinking)
    return ToolOutcome(
        result={
            "count": len(smells),
            "smells": [_smell_brief(s) for s in smells[:8]],
            "note": "Shown on screen. Mention them by number.",
        },
        state=engine.state,
        ui={"panel": "smells", "attribute": attr.value if attr else None},
    )


def _require_smell(engine: TrainerEngine, args: dict[str, Any]) -> CodeSmell | None:
    try:
        return engine.get_smell(int(args.get("smell_id")))
    except (TypeError, ValueError):
        return None


def _unknown_smell(engine: TrainerEngine, args: dict[str, Any]) -> ToolOutcome:
    return ToolOutcome(
        result={
            "error": f"There is no smell number {args.get('smell_id')}.",
            "valid_ids": [s.id for s in engine.smells],
        },
        state=engine.state,
    )


def _tool_open_smell(engine: TrainerEngine, args: dict[str, Any]) -> ToolOutcome:
    smell = _require_smell(engine, args)
    if smell is None:
        return _unknown_smell(engine, args)
    _set_pose(engine, AvatarPose.serious)
    return ToolOutcome(
        result={
            **_smell_brief(smell),
            "code": smell.code_snippet,
            "why_it_hurts": smell.tachyon_critique,
            "fix": smell.suggested_fix,
            "already_drilled_in_training": smell.drilled,
            "note": "The code is on screen. Explain it, don't read it verbatim.",
        },
        state=engine.state,
        ui={"panel": "smell", "smell_id": smell.id},
    )


def _tool_train(engine: TrainerEngine, args: dict[str, Any]) -> ToolOutcome:
    st = engine.state
    if st.is_game_over:
        return ToolOutcome(result={"error": "The training season is over."}, state=st)
    try:
        attr = AttributeType(args.get("attribute", ""))
    except ValueError:
        attr = None
    smell_id = args.get("smell_id")
    if attr is None and smell_id is None:
        return ToolOutcome(result={"error": f"attribute must be one of {_ATTRIBUTE_ENUM}"}, state=st)

    try:
        smell_id = int(smell_id) if smell_id is not None else None
    except (TypeError, ValueError):
        smell_id = None
    if smell_id is not None and engine.get_smell(smell_id) is None:
        return _unknown_smell(engine, args)
    if attr is None:
        attr = engine.get_smell(smell_id).attribute  # type: ignore[union-attr]

    result = engine.train(attr, smell_id=smell_id)
    curriculum = KnowledgeService.get_curriculum(result.attribute)
    new_state = engine.state
    return ToolOutcome(
        result={
            "success": result.success,
            "stat": result.attribute.value,
            "gained": result.stat_gained,
            "new_score": getattr(new_state.attributes, result.attribute.value),
            "energy_left": new_state.energy,
            "failure_chance_was": f"{round(result.failure_rate * 100)}%",
            "mood": new_state.mood.value,
            "drilled_smell": _smell_brief(result.smell) if result.smell else None,
            "lesson": curriculum.get("core_principle"),
            "derby_unlocked": new_state.race_unlocked,
            "season_over": new_state.is_game_over,
        },
        state=new_state,
        ui={
            "event": "train",
            "attribute": result.attribute.value,
            "success": result.success,
            "gained": result.stat_gained,
            "smell_id": result.smell.id if result.smell else None,
        },
    )


def _tool_rest(engine: TrainerEngine, _: dict[str, Any]) -> ToolOutcome:
    if engine.state.is_game_over:
        return ToolOutcome(result={"error": "The training season is over."}, state=engine.state)
    result = engine.rest()
    return ToolOutcome(
        result={
            "energy_recovered": result.energy_recovered,
            "energy": result.updated_state.energy,
            "mood": result.new_mood.value,
            "season_over": result.updated_state.is_game_over,
        },
        state=engine.state,
        ui={"event": "rest", "energy_recovered": result.energy_recovered},
    )


def _tool_rescan(engine: TrainerEngine, _: dict[str, Any]) -> ToolOutcome:
    from app.lab.findings import scan_repo_full

    repo_root = engine.repo_root
    scores, detected = scan_repo_full(repo_root)
    result = engine.rescan(scores, detected, repo_root)
    return ToolOutcome(
        result={
            "fixed": [_smell_brief(s) for s in result.fixed],
            "new_smells": [_smell_brief(s) for s in result.new],
            "remaining": result.remaining,
            "stat_changes": {k: v for k, v in result.attribute_deltas.items() if v},
        },
        state=engine.state,
        ui={
            "event": "rescan",
            "fixed": [s.id for s in result.fixed],
            "new": [s.id for s in result.new],
            "deltas": result.attribute_deltas,
        },
    )


def build_prescription(smell: CodeSmell) -> str:
    """Refactoring prompt for an AI coding agent (Claude Code, Cursor, Bob…)."""
    return (
        f"Fix one code smell in `{smell.file_path}` around line {smell.line_number}.\n\n"
        f"Problem ({smell.rule_id}, hurts {smell.attribute.value}): {smell.description}\n\n"
        f"Current code:\n```python\n{smell.code_snippet}\n```\n\n"
        f"Fix: {smell.suggested_fix}\n\n"
        "Constraints:\n"
        "- Make the minimal change that resolves this smell; don't refactor unrelated code.\n"
        "- Keep public interfaces unchanged unless strictly necessary.\n"
        "- Keep existing tests passing; add a focused test if none covers this path."
    )


def _tool_prescription(engine: TrainerEngine, args: dict[str, Any]) -> ToolOutcome:
    smell = _require_smell(engine, args)
    if smell is None:
        return _unknown_smell(engine, args)
    _set_pose(engine, AvatarPose.happy)
    return ToolOutcome(
        result={"smell": _smell_brief(smell), "note": "The prompt is on screen with a copy button. Tell them to paste it into their coding agent, then ask you to rescan."},
        state=engine.state,
        ui={"panel": "prescription", "smell_id": smell.id, "prescription": build_prescription(smell)},
    )


def _tool_start_race(engine: TrainerEngine, _: dict[str, Any]) -> ToolOutcome:
    st = engine.state
    if not (st.race_unlocked or st.is_game_over):
        remaining = st.interactions_required - st.interactions_in_cycle
        return ToolOutcome(
            result={"error": f"The Derby is locked. {remaining} more training session(s) needed."},
            state=st,
        )
    return ToolOutcome(
        result={"started": True, "note": "Checkpoint questions will arrive as game events."},
        state=st,
        ui={"view": "race"},
    )


_DISPATCH: dict[str, Callable[[TrainerEngine, dict[str, Any]], ToolOutcome]] = {
    "get_status": _tool_get_status,
    "list_smells": _tool_list_smells,
    "open_smell": _tool_open_smell,
    "train": _tool_train,
    "rest": _tool_rest,
    "rescan_repo": _tool_rescan,
    "write_fix_prescription": _tool_prescription,
    "start_race": _tool_start_race,
}


def dispatch_tool(engine: TrainerEngine, name: str, arguments: dict[str, Any] | None) -> ToolOutcome:
    """Execute a server-side tool. Unknown tools return an error result, never raise."""
    handler = _DISPATCH.get(name)
    if handler is None:
        return ToolOutcome(result={"error": f"Unknown tool '{name}'."}, state=engine.state)
    return handler(engine, arguments or {})


# ---------------------------------------------------------------------------
# Lab dispatch (async: experiments run the measurement harness)
# ---------------------------------------------------------------------------

async def dispatch(engine: TrainerEngine, lab: "LabGame", name: str, arguments: dict[str, Any] | None) -> ToolOutcome:
    """Execute any server-side tool: lab tools here, classic tools via :func:`dispatch_tool`."""
    from app.lab.game import LabError

    args = arguments or {}
    try:
        if name == "architecture_report":
            import asyncio

            from app.lab.standards import build_report

            root = lab.trainee.root if lab.mode == "lab" else engine.repo_root
            rep = await asyncio.to_thread(build_report, root)
            failing = [c for c in rep["checks"] if c["status"] != "pass"]
            result = {
                "grade": rep["grade"],
                "passed": f"{rep['passed']}/{rep['total']}",
                "modules": rep["modules"],
                "lines": rep["lines"],
                "problems": [
                    {"check": c["title"], "status": c["status"], "measured": c["value"],
                     "learn_in_chapter": c["chapter"],
                     "example": (c["evidence"][0]["file"] + ":" + str(c["evidence"][0]["line"])) if c["evidence"] else None}
                    for c in failing
                ],
                "say": ("Give the grade, name the one or two most important failing checks with where they are, and "
                        "offer to practise the matching lab chapter first. The report is on screen."),
            }
            return ToolOutcome(result=result, state=engine.state, ui={"panel": "standards"}, lab=lab.public_state())
        if name in LAB_TOOLS:
            result, ui = await _lab_call(engine, lab, name, args)
            return ToolOutcome(result=result, state=engine.state, ui=ui, lab=lab.public_state())
        if lab.mode == "lab" and name in ("train", "list_smells", "open_smell", "rescan_repo", "write_fix_prescription"):
            raise LabError("That is for the free lab on your own repository. Here we run experiments: say 'start an experiment'.")
        if lab.mode == "lab" and name == "start_race" and not engine.state.race_unlocked:
            done = len(lab.profile.chapters_cleared)
            raise LabError(f"The Derby is locked: {done} of {engine.state.interactions_required} experiments cleared this career.")
        if lab.mode == "lab" and name == "rest" and not engine.state.is_game_over:
            lab.close_experiment()
            lab.close_review()
            out = dispatch_tool(engine, name, args)
            lab.rest(engine)
            return out.model_copy(update={"state": engine.state, "lab": lab.public_state()})
        out = dispatch_tool(engine, name, args)
        if name == "get_status" and lab.mode == "lab":
            out.result["lab"] = {
                "career": lab.profile.career, "bond": lab.profile.bond, "title": lab.profile.title,
                "experiments_cleared": lab.profile.chapters_cleared, "due_reviews": lab.profile.due_concepts(),
                "next_experiment": (lab.next_chapter().id if lab.next_chapter() else None),
            }
        return out.model_copy(update={"lab": lab.public_state()})
    except LabError as err:
        return ToolOutcome(result={"error": str(err)}, state=engine.state, lab=lab.public_state())


async def _lab_call(engine: TrainerEngine, lab: "LabGame", name: str, args: dict[str, Any]) -> tuple[dict, dict]:
    if name == "start_experiment":
        lab.close_review()
        return await lab.start_experiment(engine, args.get("chapter"))
    if name == "submit_prediction":
        return lab.submit_prediction(engine, args.get("option"), args.get("confidence", "likely"))
    if name == "present_evidence":
        return lab.present_evidence(engine, args.get("line"))
    if name == "submit_explanation":
        return lab.submit_explanation(engine, args.get("explanation"))
    if name == "get_hint":
        return lab.hint(engine)
    if name == "choose_fix":
        return await lab.choose_fix(engine, args.get("option"))
    if name == "keep_fix":
        return lab.keep_fix(engine)
    if name == "revert_fix":
        return await lab.revert_fix(engine)
    if name == "abandon_experiment":
        return await lab.abandon_experiment(engine)
    if name == "start_review":
        return lab.start_review(engine)
    if name == "answer_review":
        return lab.answer_review(engine, args.get("option"))
    raise ValueError(name)

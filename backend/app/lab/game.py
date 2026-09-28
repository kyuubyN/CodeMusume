"""The lab career: experiments, reviews, the Derby, and what carries over.

``LabGame`` owns everything that is not the classic turn/energy/mood state
(which stays in :class:`TrainerEngine`): the trainee's working copy, the
latest measurements, the active experiment or review, and the trainer's
persistent profile. Every method takes the engine explicitly, so the voice
tools and the on-screen buttons drive exactly the same code.

Each public action returns ``(result, ui)``: ``result`` is what the voice
agent's LLM reads (including a ``say`` hint for what to do next), ``ui`` tells
the screen what to show.
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import Any

from app.lab import fitness
from app.lab.analysis import analyze_repo
from app.lab.chapters import CHAPTER_BY_ID, CHAPTERS, Chapter, Evidence
from app.lab.grader import grade
from app.lab.harness.runner import run_all, run_workload_async
from app.lab.profile import HallEntry, Profile, ProfileStore, now_iso
from app.lab.reviews import BY_CONCEPT, BY_ID, REVIEW_BANK, ReviewQuestion
from app.lab.trainee import Trainee
from app.models.schemas import (
    AttributeScores,
    AttributeType,
    AvatarPose,
    GameState,
    MoodState,
    RaceRival,
    score_to_rank,
)
from app.services.trainer_service import TrainerEngine

EXPERIMENT_ENERGY = 20
HINT_ENERGY = 5
RETRY_ENERGY = 5
REVIEW_ENERGY = 10
MAX_TURNS = 12
EXPERIMENTS_TO_QUALIFY = 3
CONFIDENCE = {1: "guess", 2: "likely", 3: "certain"}
_MOOD_ORDER = [MoodState.TERRIBLE, MoodState.POOR, MoodState.NORMAL, MoodState.GOOD, MoodState.GREAT]
_MOOD_MULT = {MoodState.TERRIBLE: 0.9, MoodState.POOR: 0.95, MoodState.NORMAL: 1.0, MoodState.GOOD: 1.05, MoodState.GREAT: 1.1}
_ATTR_ORDER = [AttributeType.SPEED, AttributeType.STAMINA, AttributeType.POWER, AttributeType.GUTS, AttributeType.WISDOM]


class LabError(Exception):
    """An action that is not allowed right now; the message is spoken to the trainer."""


@dataclass
class FixTry:
    key: str
    verdict: str
    result: dict
    score: int
    static: str


@dataclass
class Experiment:
    chapter: Chapter
    stage: str                                   # predict → evidence → explain → fix → reprove → debrief
    eureka: bool
    baseline: dict
    baseline_score: int
    options: list[str]
    correct_index: int
    code_file: str
    code: list[str]
    evidence: Evidence
    prediction: dict | None = None
    evidence_attempts: list[int] = field(default_factory=list)
    evidence_found: str | None = None            # "best" | "ok" | "revealed"
    explanations: list[str] = field(default_factory=list)
    hits: list[str] = field(default_factory=list)
    follow_up: str | None = None
    hints: list[str] = field(default_factory=list)
    explain_hints: int = 0
    tries: list[FixTry] = field(default_factory=list)
    current_fix: str | None = None
    points: dict[str, int] = field(default_factory=dict)
    summary: dict | None = None


@dataclass
class ActiveReview:
    question: ReviewQuestion
    answered: int | None = None


class LabGame:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        self.store = ProfileStore(os.path.join(data_dir, "profile.json"))
        self.profile: Profile = self.store.load()
        self.trainee = Trainee(os.path.join(data_dir, "trainee"))
        self.results: dict[str, dict] = {}
        self.mode = "lab"
        self.experiment: Experiment | None = None
        self.review: ActiveReview | None = None
        self.derby: dict[str, Any] | None = None
        self.rng = random.Random()

    def save(self) -> None:
        self.store.save(self.profile)

    # ------------------------------------------------------------------ #
    # Career lifecycle
    # ------------------------------------------------------------------ #

    async def start_career(self, fresh: bool = False) -> GameState:
        """Begin (or resume) a career on the lab specimen."""
        resume = not fresh and os.path.isdir(self.trainee.root) and self.profile.run is not None
        if not resume:
            self.trainee.reset()
            self.profile.chapters_cleared = []
            self.profile.chapter_scores = {}
            self.profile.fixes = {}
            self.profile.run = None
        else:
            # An experiment interrupted by a restart may have left a treatment applied.
            for ch in CHAPTERS:
                if ch.id not in self.profile.chapters_cleared:
                    self.trainee.revert(ch)
        self.mode = "lab"
        self.experiment = None
        self.review = None
        self.derby = None
        self.results = await run_all(self.trainee.root)
        run = self.profile.run or {}
        state = GameState(
            mode="lab",
            repo_name="tachyon_lab",
            turn=run.get("turn", 1),
            max_turns=MAX_TURNS,
            energy=run.get("energy", 100),
            mood=MoodState(run.get("mood", "normal")),
            attributes=self.attributes(),
            current_pose=AvatarPose.idle,
            dialogue="",
            interactions_in_cycle=len(self.profile.chapters_cleared),
            interactions_required=EXPERIMENTS_TO_QUALIFY,
        )
        state.race_unlocked = self._derby_ready(state)
        state.is_game_over = state.turn > state.max_turns
        self._persist_run(state)
        return state

    def _persist_run(self, state: GameState) -> None:
        self.profile.run = {"turn": state.turn, "energy": state.energy, "mood": state.mood.value}
        self.save()

    def _derby_ready(self, state: GameState) -> bool:
        return len(self.profile.chapters_cleared) >= EXPERIMENTS_TO_QUALIFY or state.turn > state.max_turns

    def attributes(self) -> AttributeScores:
        values: dict[str, int] = {}
        for ch in CHAPTERS:
            res = self.results.get(ch.workload, {})
            mastery = self.profile.concept(ch.concept).mastery
            values[ch.attribute.value] = fitness.score(ch.attribute, res, mastery)
        return AttributeScores(**values)

    def _sync(self, engine: TrainerEngine, **update: Any) -> GameState:
        """Write lab-derived fields into the engine state and persist the run."""
        st = engine.state.model_copy(update={"attributes": self.attributes(), "mode": "lab", **update})
        st.interactions_in_cycle = len(self.profile.chapters_cleared)
        st.race_unlocked = self._derby_ready(st)
        st.is_game_over = st.turn > st.max_turns
        engine.state = st
        self._persist_run(st)
        return st

    def _require_lab(self) -> None:
        if self.mode != "lab":
            raise LabError("Experiments run on my lab specimen. Switch back to the lab first.")

    def _spend(self, engine: TrainerEngine, energy: int) -> None:
        if engine.state.energy < energy:
            raise LabError(f"You need {energy} energy for that and have {engine.state.energy}. Rest first.")
        engine.state = engine.state.model_copy(update={"energy": engine.state.energy - energy})

    def _advance_turn(self, engine: TrainerEngine, mood_step: int = 0) -> None:
        st = engine.state
        idx = _MOOD_ORDER.index(st.mood)
        mood = _MOOD_ORDER[max(0, min(len(_MOOD_ORDER) - 1, idx + mood_step))]
        engine.state = st.model_copy(update={"turn": st.turn + 1, "mood": mood})
        self.profile.lab_day += 1

    def _pose(self, engine: TrainerEngine, pose: AvatarPose) -> None:
        engine.state = engine.state.model_copy(update={"current_pose": pose})

    # ------------------------------------------------------------------ #
    # Experiments
    # ------------------------------------------------------------------ #

    def _chapter(self, chapter_id: Any) -> Chapter:
        try:
            ch = CHAPTER_BY_ID[int(chapter_id)]
        except (TypeError, ValueError, KeyError):
            raise LabError(f"There is no experiment {chapter_id}. Chapters are 1 to {len(CHAPTERS)}.") from None
        return ch

    def next_chapter(self) -> Chapter | None:
        return next((c for c in CHAPTERS if c.id not in self.profile.chapters_cleared), None)

    async def start_experiment(self, engine: TrainerEngine, chapter_id: Any = None) -> tuple[dict, dict]:
        self._require_lab()
        if self.experiment and self.experiment.stage != "debrief":
            ch = self.experiment.chapter
            raise LabError(f"Experiment {ch.id}, {ch.title}, is still running. Finish or abandon it first.")
        if engine.state.is_game_over:
            raise LabError("The season is over. Only the Grand Derby remains.")
        ch = self._chapter(chapter_id) if chapter_id not in (None, "", 0) else self.next_chapter()
        if ch is None:
            raise LabError("Every experiment in this career is complete. Review, rest, or run the Derby.")
        if ch.id in self.profile.chapters_cleared:
            raise LabError(f"You already cleared {ch.title} in this career.")
        self._spend(engine, EXPERIMENT_ENERGY)
        self.review = None

        baseline = await run_workload_async(ch.workload, self.trainee.root)
        options, correct = ch.build_options(baseline)
        analysis = analyze_repo(self.trainee.root)
        evidence = ch.find_evidence(analysis, self.trainee.root)
        code = self.trainee.read(evidence.file).splitlines()
        eureka = self.rng.random() < max(0.0, min(0.45, (self.profile.bond - 50) / 100))
        mastery = self.profile.concept(ch.concept).mastery
        self.experiment = Experiment(
            chapter=ch, stage="predict", eureka=eureka, baseline=baseline,
            baseline_score=fitness.score(ch.attribute, baseline, mastery),
            options=options, correct_index=correct, code_file=evidence.file, code=code, evidence=evidence,
        )
        self._pose(engine, AvatarPose.flow if eureka else AvatarPose.thinking)
        self._sync(engine)
        lines = list(ch.intro)
        if eureka:
            lines.insert(0, "Eureka! Our bond is resonating. This experiment's results will be amplified.")
        result = {
            "experiment": ch.id,
            "title": ch.title,
            "concept": ch.concept_title,
            "question": ch.question,
            "options": {"ABCD"[i]: o for i, o in enumerate(options)},
            "eureka": eureka,
            "say": ("Briefly set the scene in one sentence, then read the question and the four options aloud "
                    "and ask how confident they are: guess, likely or certain. Then call submit_prediction."),
        }
        return result, {"panel": "experiment", "event": "experiment_start", "script": lines}

    def _exp(self, *stages: str) -> Experiment:
        exp = self.experiment
        if exp is None:
            raise LabError("No experiment is running. Start one first.")
        if stages and exp.stage not in stages:
            raise LabError(f"We are in the {exp.stage} step of the experiment, not that one.")
        return exp

    def submit_prediction(self, engine: TrainerEngine, option: Any, confidence: Any = 2) -> tuple[dict, dict]:
        exp = self._exp("predict")
        idx = _option_index(option, len(exp.options))
        conf = _confidence(confidence)
        correct = idx == exp.correct_index
        self.profile.record_prediction(correct, conf)
        exp.prediction = {"index": idx, "confidence": conf, "correct": correct}
        exp.points["prediction"] = (15 + (5 if conf == 3 else 0)) if correct else 0
        exp.stage = "evidence"
        ch = exp.chapter
        if correct:
            line, pose = ch.reveal_right, AvatarPose.happy
        elif conf == 3:
            line, pose = ch.reveal_certain_wrong, AvatarPose.crazy
        else:
            line, pose = ch.reveal_wrong, AvatarPose.shocked
        self._pose(engine, pose)
        self._sync(engine)
        h = exp.baseline.get("headline", {})
        result = {
            "correct": correct,
            "confidence": CONFIDENCE[conf],
            "answer": "ABCD"[exp.correct_index],
            "answer_text": exp.options[exp.correct_index],
            "measured": f"{h.get('label')}: {h.get('value')} {h.get('unit', '')}".strip(),
            "metrics": exp.baseline.get("metrics"),
            "certain_and_wrong": (not correct and conf == 3),
            "next_step": ch.evidence_prompt,
            "say": ("React to the measurement in one or two sentences (celebrate, or relish a confident miss), "
                    "then ask them to present the culprit line on screen or say its line number. "
                    "Do not reveal the line. Then call present_evidence."),
        }
        return result, {"panel": "experiment", "event": "prediction", "correct": correct, "script": [line, ch.evidence_prompt]}

    def present_evidence(self, engine: TrainerEngine, line: Any) -> tuple[dict, dict]:
        exp = self._exp("evidence")
        try:
            n = int(line)
        except (TypeError, ValueError):
            raise LabError("Give me a line number from the code on screen.") from None
        if n < 1 or n > len(exp.code):
            raise LabError(f"The file only has {len(exp.code)} lines.")
        ch = exp.chapter
        ev = exp.evidence
        if n in exp.evidence_attempts and n not in ev.best and n not in ev.ok:
            # Presenting the same wrong line twice costs nothing and teaches nothing.
            return (
                {"accepted": False, "line": n, "repeat": True, "attempts_left": 3 - len(exp.evidence_attempts),
                 "say": "Remind them they already tried that line."},
                {"panel": "experiment", "event": "evidence", "accepted": False,
                 "script": [f"Line {n} again? I already rejected it. Look elsewhere."]},
            )
        exp.evidence_attempts.append(n)
        attempt = len(exp.evidence_attempts)
        if n in ev.best or n in ev.ok:
            quality = "best" if n in ev.best else "ok"
            exp.evidence_found = quality
            table = {1: 25 if quality == "best" else 18, 2: 12, 3: 6}
            exp.points["evidence"] = table.get(attempt, 4)
            exp.stage = "explain"
            self._pose(engine, AvatarPose.serious)
            self._sync(engine)
            line_text = ch.evidence_right if quality == "best" else (
                "Close. That line is part of the crime, but the root is nearby. I will accept it.")
            result = {
                "accepted": True, "line": n, "code": exp.code[n - 1].strip(), "quality": quality,
                "root_cause_lines": sorted(ev.best),
                "say": f"Confirm the evidence in one sentence, then ask: {ch.explain_prompt} Wait for their spoken explanation and call submit_explanation with it verbatim.",
            }
            return result, {"panel": "experiment", "event": "evidence", "accepted": True, "script": [line_text, ch.explain_prompt]}

        penalty = 3 if attempt < 3 else 0
        if penalty:
            engine.state = engine.state.model_copy(update={"energy": max(0, engine.state.energy - penalty)})
        why = ev.wrong_hints.get(n, ch.evidence_wrong)
        if attempt >= 3:
            exp.evidence_found = "revealed"
            exp.points["evidence"] = 0
            exp.stage = "explain"
            best = sorted(ev.best)
            self._pose(engine, AvatarPose.serious)
            self._sync(engine)
            reveal = f"Three strikes. The culprit is line {best[0] if best else '?'}: {exp.code[best[0] - 1].strip() if best else ''}"
            return (
                {"accepted": False, "revealed_line": best[0] if best else None,
                 "say": f"Reveal the culprit line kindly, then ask: {ch.explain_prompt} Call submit_explanation with their answer."},
                {"panel": "experiment", "event": "evidence", "accepted": False, "script": [reveal, ch.explain_prompt]},
            )
        self._pose(engine, AvatarPose.thinking)
        self._sync(engine)
        return (
            {"accepted": False, "line": n, "attempts_left": 3 - attempt, "energy_cost": penalty,
             "say": "Tell them that line is not the culprit, with a nudge but not the answer, and let them try again."},
            {"panel": "experiment", "event": "evidence", "accepted": False, "script": [why]},
        )

    def submit_explanation(self, engine: TrainerEngine, text: Any) -> tuple[dict, dict]:
        exp = self._exp("explain")
        ch = exp.chapter
        text = str(text or "").strip()
        exp.explanations.append(text)
        g = grade(text, ch.rubric, set(exp.hits))
        exp.hits = g.hits
        labels = {k.id: k.label for k in ch.rubric}
        done = g.score >= 0.66 or len(exp.explanations) >= 2
        exp.follow_up = None if done else g.follow_up
        if done:
            exp.points["explanation"] = max(0, round(35 * g.score) - 5 * exp.explain_hints)
            exp.stage = "fix"
            pose = AvatarPose.happy if g.score >= 0.66 else AvatarPose.serious
            missed_labels = [labels[m] for m in g.missed]
            script = []
            if g.score >= 0.99:
                script.append("A complete explanation. I could not have put it better. Well, slightly better.")
            elif g.score >= 0.66:
                script.append(f"Good. You only skipped one thing: {missed_labels[0].lower()}." if missed_labels else "Good.")
            else:
                script.append("Let me complete the picture: " + "; ".join(m.lower() for m in missed_labels) + ".")
            script.append(ch.fix_prompt)
            say = ("Give a one-sentence verdict on their explanation, filling in anything they missed, then ask them "
                   "to choose a treatment on screen or by letter, and call choose_fix.")
        else:
            pose = AvatarPose.thinking
            script = [f"Half right. {g.follow_up}"]
            say = (f"Do not give the answer. Ask exactly this follow-up in your own words: '{g.follow_up}' "
                   "Then call submit_explanation again with their new answer.")
        self._pose(engine, pose)
        self._sync(engine)
        result = {
            "heard": [labels[h] for h in g.hits],
            "missing": [labels[m] for m in g.missed],
            "score": round(g.score, 2),
            "follow_up": exp.follow_up,
            "fix_options": {f.key: f.label for f in ch.fixes} if done else None,
            "say": say,
        }
        return result, {"panel": "experiment", "event": "explanation", "script": script}

    def hint(self, engine: TrainerEngine) -> tuple[dict, dict]:
        exp = self._exp("predict", "evidence", "explain")
        pool = exp.chapter.hints.get(exp.stage, [])
        used = [h for h in exp.hints if h in pool]
        if len(used) >= len(pool):
            raise LabError("I have no more hints for this step. Think, Morumotto-kun!")
        self._spend(engine, HINT_ENERGY)
        tip = pool[len(used)]
        exp.hints.append(tip)
        if exp.stage == "explain":
            exp.explain_hints += 1
        self._sync(engine)
        return (
            {"hint": tip, "energy_cost": HINT_ENERGY, "say": "Give this hint in character, as a question if you can, without revealing the answer."},
            {"panel": "experiment", "event": "hint", "script": [tip]},
        )

    async def choose_fix(self, engine: TrainerEngine, option: Any) -> tuple[dict, dict]:
        exp = self._exp("fix", "reprove")
        ch = exp.chapter
        keys = [f.key for f in ch.fixes]
        key = str(option or "").strip().upper()[:1]
        if key not in keys:
            raise LabError(f"Choose one of {', '.join(keys)}.")
        if exp.tries:
            self._spend(engine, RETRY_ENERGY)
        fix = next(f for f in ch.fixes if f.key == key)
        self.trainee.apply(ch, key)
        after = await run_workload_async(ch.workload, self.trainee.root)
        self.results[ch.workload] = after
        static = _static_verdict(ch, self.trainee.root)
        mastery = self.profile.concept(ch.concept).mastery
        s = fitness.score(ch.attribute, after, mastery)
        exp.tries.append(FixTry(key, fix.verdict, after, s, static))
        exp.current_fix = key
        exp.stage = "reprove"
        good = fix.verdict in ("best", "good")
        self._pose(engine, AvatarPose.happy if good else AvatarPose.shocked)
        self._sync(engine)
        before_h = exp.baseline.get("headline", {})
        after_h = after.get("headline", {})
        result = {
            "fix": f"{key}: {fix.label}",
            "verdict": fix.verdict,
            "before": f"{before_h.get('value')} {before_h.get('unit', '')}".strip(),
            "after": f"{after_h.get('value')} {after_h.get('unit', '')}".strip() if after_h else after.get("error"),
            "stat": ch.attribute.value,
            "stat_before": exp.baseline_score,
            "stat_after": s,
            "static_analysis": static,
            "lesson": fix.lesson,
            "say": ("Report before and after with the real numbers and explain the lesson in two sentences. "
                    + ("Then ask if they want to keep this fix (call keep_fix) or try another (call choose_fix)."
                       if good else "Encourage them to try another treatment (call choose_fix with another letter).")),
        }
        return result, {"panel": "experiment", "event": "fix", "verdict": fix.verdict, "script": [fix.lesson]}

    async def revert_fix(self, engine: TrainerEngine) -> tuple[dict, dict]:
        exp = self._exp("reprove")
        self.trainee.revert(exp.chapter)
        self.results[exp.chapter.workload] = await run_workload_async(exp.chapter.workload, self.trainee.root)
        exp.current_fix = None
        exp.stage = "fix"
        self._sync(engine)
        return ({"reverted": True, "say": "Say the code is back to its original state and ask which treatment to try."},
                {"panel": "experiment", "event": "revert", "script": ["Reverted. The specimen is sick again. Choose another treatment."]})

    def keep_fix(self, engine: TrainerEngine) -> tuple[dict, dict]:
        exp = self._exp("reprove")
        ch = exp.chapter
        first = exp.tries[0]
        final = exp.tries[-1]
        fix_pts = {"best": 20, "good": 15, "partial": 8, "wrong": 0}
        exp.points["fix"] = fix_pts[final.verdict] if len(exp.tries) == 1 else (8 if final.verdict in ("best", "good") else 3)
        raw = sum(exp.points.values())
        mult = _MOOD_MULT[engine.state.mood] * (1.5 if exp.eureka else 1.0)
        score = min(100, round(raw * mult))

        rec = self.profile.concept(ch.concept)
        before_mastery = rec.mastery
        rec.mastery = max(rec.mastery, score)
        rec.best_score = max(rec.best_score, score)
        rec.experiments += 1

        explained = exp.points.get("explanation", 0) >= 23
        bond = 5 + (3 if explained else 0) + (2 if exp.prediction and exp.prediction["correct"] else 0)
        if exp.eureka:
            bond *= 2
        title_before = self.profile.title
        self.profile.add_bond(bond)
        self.profile.chapters_cleared.append(ch.id)
        self.profile.chapter_scores[str(ch.id)] = score
        self.profile.fixes[str(ch.id)] = final.key
        new_lore = ch.id not in self.profile.journal
        if new_lore:
            self.profile.journal.append(ch.id)

        mood_step = 1 if score >= 75 else -1 if score < 35 else 0
        self._advance_turn(engine, mood_step)
        self.profile.schedule(ch.concept, score >= 60)
        st = self._sync(engine, current_pose=AvatarPose.happy if score >= 60 else AvatarPose.serious)
        attr_after = getattr(st.attributes, ch.attribute.value)

        exp.summary = {
            "chapter": ch.id,
            "title": ch.title,
            "score": score,
            "points": dict(exp.points),
            "multiplier": round(mult, 2),
            "eureka": exp.eureka,
            "mastery_before": before_mastery,
            "mastery_after": rec.mastery,
            "next_review_in_days": rec.due_day - self.profile.lab_day,
            "stat": ch.attribute.value,
            "stat_before": exp.baseline_score,
            "stat_after": attr_after,
            "rank_after": score_to_rank(attr_after).value,
            "fix": final.key,
            "fix_verdict": final.verdict,
            "first_fix_verdict": first.verdict,
            "bond_gained": bond,
            "bond": self.profile.bond,
            "bond_title": self.profile.title,
            "title_up": self.profile.title != title_before,
            "lore": {"title": ch.lore_title, "text": ch.lore} if new_lore else None,
            "takeaway": ch.takeaway,
            "derby_unlocked": st.race_unlocked,
        }
        exp.stage = "debrief"
        self.save()
        script = list(ch.outro)
        if exp.summary["title_up"]:
            script.append(f"You are no longer a mere subject. From today you are my {self.profile.title}.")
        return (
            {**exp.summary, "say": "Wrap up the experiment in two sentences: the takeaway and one thing they did well. "
                                   "Mention if the Derby is now unlocked. Then suggest the next experiment, a review, or rest."},
            {"panel": "experiment", "event": "debrief", "score": score, "eureka": exp.eureka, "script": script},
        )

    def close_experiment(self) -> None:
        if self.experiment and self.experiment.stage == "debrief":
            self.experiment = None

    async def abandon_experiment(self, engine: TrainerEngine) -> tuple[dict, dict]:
        exp = self._exp()
        if exp.stage == "debrief":
            self.experiment = None
            return {"closed": True}, {"panel": "lab"}
        self.trainee.revert(exp.chapter)
        self.results[exp.chapter.workload] = await run_workload_async(exp.chapter.workload, self.trainee.root)
        self.experiment = None
        self.profile.add_bond(-3)
        self._advance_turn(engine, -1)
        self._sync(engine, current_pose=AvatarPose.tired)
        return (
            {"abandoned": True, "say": "Grumble briefly about an unfinished experiment, in character."},
            {"panel": "lab", "event": "abandon", "script": ["An experiment abandoned… The data weeps, Morumotto-kun."]},
        )

    # ------------------------------------------------------------------ #
    # Spaced review
    # ------------------------------------------------------------------ #

    def start_review(self, engine: TrainerEngine, concept: str | None = None) -> tuple[dict, dict]:
        if self.experiment and self.experiment.stage != "debrief":
            raise LabError("Finish the experiment first.")
        if engine.state.is_game_over:
            raise LabError("The season is over. Only the Grand Derby remains.")
        due = self.profile.due_concepts()
        studied = [k for k, r in self.profile.concepts.items() if r.box > 0]
        pool = [concept] if concept in BY_CONCEPT else (due or studied)
        if not pool:
            raise LabError("There is nothing to review yet. Run an experiment first.")
        self._spend(engine, REVIEW_ENERGY)
        self.experiment = None
        key = pool[0]
        questions = BY_CONCEPT[key]
        asked = self.profile.concept(key).reviews_right + self.profile.concept(key).reviews_wrong
        q = questions[asked % len(questions)]
        self.review = ActiveReview(q)
        self._pose(engine, AvatarPose.serious)
        self._sync(engine)
        return (
            {"review": q.id, "concept": q.concept, "question": q.prompt, "code": q.code,
             "options": {"ABCD"[i]: o for i, o in enumerate(q.options)},
             "say": "Pop quiz! Read the question and the four options aloud, briefly, then call answer_review with their letter."},
            {"panel": "review", "event": "review_start", "script": ["Pop quiz, Morumotto-kun! Let us see if it stuck.", q.prompt]},
        )

    def answer_review(self, engine: TrainerEngine, option: Any) -> tuple[dict, dict]:
        r = self.review
        if r is None or r.answered is not None:
            raise LabError("There is no open review question.")
        q = r.question
        idx = _option_index(option, len(q.options))
        r.answered = idx
        correct = idx == q.correct
        rec = self.profile.concept(q.concept)
        if correct:
            rec.reviews_right += 1
            rec.mastery = min(100, rec.mastery + 5)
            self.profile.add_bond(3)
        else:
            rec.reviews_wrong += 1
            rec.mastery = max(0, rec.mastery - 5)
        self._advance_turn(engine)
        self.profile.schedule(q.concept, correct)
        self._sync(engine, current_pose=AvatarPose.happy if correct else AvatarPose.shocked)
        return (
            {"correct": correct, "answer": "ABCD"[q.correct], "explanation": q.explanation,
             "mastery": rec.mastery, "next_review_in_days": rec.due_day - self.profile.lab_day,
             "say": "Say whether they got it right and give the one-sentence explanation."},
            {"panel": "review", "event": "review_answer", "correct": correct,
             "script": [("Correct! " if correct else "Wrong. ") + q.explanation]},
        )

    def close_review(self) -> None:
        if self.review and self.review.answered is not None:
            self.review = None

    def rest(self, engine: TrainerEngine) -> None:
        self.profile.lab_day += 1
        if self.mode == "lab":
            self._sync(engine)

    # ------------------------------------------------------------------ #
    # Grand Derby
    # ------------------------------------------------------------------ #

    def skills(self) -> list[dict]:
        out = []
        for ch in CHAPTERS:
            rec = self.profile.concept(ch.concept)
            level = self.profile.sparks.get(ch.concept, 0) + (1 if rec.mastery >= 70 else 0)
            if level:
                out.append({"concept": ch.concept, "title": ch.concept_title, "stat": ch.attribute.value, "level": level})
        return out

    def rivals(self) -> list[RaceRival]:
        best = self.profile.best_career()
        rivals = [
            RaceRival(id="legacy-monolith", name="Legacy Monolith", architecture_style="monolith",
                      attributes=AttributeScores(speed=250, stamina=750, power=300, guts=150, wisdom=350)),
            RaceRival(id="uncached-script", name="Uncached Script", architecture_style="script",
                      attributes=AttributeScores(speed=650, stamina=120, power=200, guts=100, wisdom=150)),
        ]
        if best is not None:
            rivals.append(RaceRival(id="ghost", name=f"Ghost of career {best.career}", architecture_style="ghost",
                                    attributes=AttributeScores(**best.attributes)))
        else:
            rivals.append(RaceRival(id="ghost", name="Agnes's Prototype", architecture_style="ghost",
                                    attributes=AttributeScores(speed=600, stamina=600, power=600, guts=600, wisdom=600)))
        return rivals

    def race_attributes(self) -> AttributeScores:
        attrs = self.attributes().model_dump()
        for s in self.skills():
            attrs[s["stat"]] += 60 * s["level"]
        return AttributeScores(**attrs)

    def derby_questions(self) -> list[ReviewQuestion]:
        """Three checkpoint questions, one per concept where possible, from this career's chapters."""
        studied = [c.concept for c in CHAPTERS if c.id in self.profile.chapters_cleared] or [c.concept for c in CHAPTERS]
        pool = [q for q in REVIEW_BANK if q.concept in studied]
        self.rng.shuffle(pool)
        picks: list[ReviewQuestion] = []
        for q in pool:
            if q.concept not in {p.concept for p in picks}:
                picks.append(q)
        for q in pool:
            if len(picks) >= 3:
                break
            if q not in picks:
                picks.append(q)
        return picks[:3]

    def answer_checkpoint(self, qid: str, index: int) -> dict:
        q = BY_ID.get(qid)
        if q is None:
            raise LabError("Unknown checkpoint question.")
        correct = int(index) == q.correct
        rec = self.profile.concept(q.concept)
        if correct:
            rec.mastery = min(100, rec.mastery + 2)
        self.save()
        return {"correct": correct, "correct_index": q.correct, "explanation": q.explanation,
                "speed_delta": 3.0 if correct else -1.8}

    def complete_career(self, engine: TrainerEngine, place: int, checkpoint_score: int) -> dict:
        sparks_earned: dict[str, int] = {}
        for ch in CHAPTERS:
            s = self.profile.chapter_scores.get(str(ch.id))
            if s is None or s < 60:
                continue
            stars = 3 if s >= 95 else 2 if s >= 80 else 1
            sparks_earned[ch.concept] = stars
            self.profile.sparks[ch.concept] = max(self.profile.sparks.get(ch.concept, 0), stars)
        entry = HallEntry(
            career=self.profile.career,
            finished_at=now_iso(),
            trainee="tachyon_lab" if self.mode == "lab" else engine.state.repo_name,
            place=place,
            checkpoint_score=checkpoint_score,
            attributes=engine.state.attributes.model_dump(),
            chapters_cleared=list(self.profile.chapters_cleared),
            sparks=sparks_earned,
        )
        self.profile.hall.append(entry)
        self.profile.add_bond(8 if place == 1 else 4)
        self.profile.career += 1
        self.profile.run = None
        self.save()
        engine.state = engine.state.model_copy(update={"is_game_over": True, "race_unlocked": False})
        return {"hall_entry": entry.model_dump(), "sparks_earned": sparks_earned, "bond": self.profile.bond,
                "title": self.profile.title, "next_career": self.profile.career}

    # ------------------------------------------------------------------ #
    # Screen state
    # ------------------------------------------------------------------ #

    def public_state(self) -> dict:
        p = self.profile
        mastery_map = []
        for ch in CHAPTERS:
            rec = p.concept(ch.concept)
            mastery_map.append({
                "concept": ch.concept, "title": ch.concept_title, "stat": ch.attribute.value, "chapter": ch.id,
                "mastery": rec.mastery, "box": rec.box,
                "due": rec.box > 0 and rec.due_day <= p.lab_day,
                "due_in": max(0, rec.due_day - p.lab_day) if rec.box else None,
                "sparks": p.sparks.get(ch.concept, 0),
                "reviews": [rec.reviews_right, rec.reviews_wrong],
            })
        chapters = []
        for ch in CHAPTERS:
            res = self.results.get(ch.workload, {})
            status = "cleared" if ch.id in p.chapters_cleared else (
                "active" if self.experiment and self.experiment.chapter.id == ch.id and self.experiment.stage != "debrief" else "open")
            chapters.append({
                "id": ch.id, "slug": ch.slug, "title": ch.title, "concept": ch.concept_title, "stat": ch.attribute.value,
                "status": status, "score": p.chapter_scores.get(str(ch.id)), "fix": p.fixes.get(str(ch.id)),
                "measure": res.get("headline"), "error": res.get("error"),
            })
        return {
            "mode": self.mode,
            "career": p.career,
            "lab_day": p.lab_day,
            "bond": p.bond,
            "title": p.title,
            "calibration": p.calibration,
            "predictions": [p.predictions_right, p.predictions],
            "certain": [p.certain_right, p.certain_wrong],
            "chapters": chapters,
            "mastery": mastery_map,
            "due": p.due_concepts(),
            "sparks": p.sparks,
            "skills": self.skills(),
            "hall": [h.model_dump() for h in p.hall[-6:]],
            "journal": [{"chapter": c, "title": CHAPTER_BY_ID[c].lore_title, "text": CHAPTER_BY_ID[c].lore}
                        for c in p.journal if c in CHAPTER_BY_ID],
            "experiment": self._experiment_view(),
            "review": self._review_view(),
            "experiments_done": len(p.chapters_cleared),
            "experiments_required": EXPERIMENTS_TO_QUALIFY,
        }

    def _experiment_view(self) -> dict | None:
        exp = self.experiment
        if exp is None:
            return None
        ch = exp.chapter
        predicted = exp.prediction is not None
        found = exp.evidence_found is not None
        labels = {k.id: k.label for k in ch.rubric}
        tried = {t.key: t for t in exp.tries}
        current = tried.get(exp.current_fix) if exp.current_fix else None
        return {
            "chapter": ch.id,
            "title": ch.title,
            "concept": ch.concept_title,
            "stat": ch.attribute.value,
            "stage": exp.stage,
            "eureka": exp.eureka,
            "intro": ch.intro,
            "question": ch.question,
            "options": exp.options,
            "prediction": exp.prediction,
            "correct_index": exp.correct_index if predicted else None,
            "baseline": _result_view(exp.baseline) if predicted else None,
            "baseline_score": exp.baseline_score,
            "code_file": exp.code_file,
            "code": exp.code,
            "evidence_prompt": ch.evidence_prompt,
            "evidence_attempts": exp.evidence_attempts,
            "evidence_found": exp.evidence_found,
            "evidence_lines": sorted(exp.evidence.best) if found else [],
            "evidence_ok_lines": sorted(exp.evidence.ok) if found else [],
            "explain_prompt": ch.explain_prompt,
            "explanations": exp.explanations,
            "rubric": [{"id": k.id, "label": k.label, "hit": k.id in exp.hits} for k in ch.rubric]
            if exp.explanations else [],
            "rubric_revealed": exp.stage in ("fix", "reprove", "debrief"),
            "follow_up": exp.follow_up,
            "hints": exp.hints,
            "hints_left": max(0, len(ch.hints.get(exp.stage, [])) - len([h for h in exp.hints if h in ch.hints.get(exp.stage, [])])),
            "fix_prompt": ch.fix_prompt,
            "fixes": [
                {"key": f.key, "label": f.label, "detail": f.detail,
                 "verdict": f.verdict if f.key in tried else None,
                 "lesson": f.lesson if f.key in tried else None,
                 "diff": self.trainee.diff(ch, f.key)}
                for f in ch.fixes
            ],
            "tries": [{"key": t.key, "verdict": t.verdict, "score": t.score, "static": t.static,
                       "result": _result_view(t.result)} for t in exp.tries],
            "current_fix": exp.current_fix,
            "after": _result_view(current.result) if current else None,
            "after_score": current.score if current else None,
            "points": exp.points,
            "summary": exp.summary,
            "labels": labels,
        }

    def _review_view(self) -> dict | None:
        r = self.review
        if r is None:
            return None
        q = r.question
        return {
            "id": q.id, "concept": q.concept, "prompt": q.prompt, "code": q.code, "options": list(q.options),
            "answered": r.answered,
            "correct_index": q.correct if r.answered is not None else None,
            "explanation": q.explanation if r.answered is not None else None,
        }

    def trainee_symbols(self) -> list[str]:
        """File and function names in the trainee, for speech-recognition keyterms."""
        import ast

        from app.lab.analysis.callgraph import iter_py_files

        names: list[str] = []
        for path in iter_py_files(self.trainee.root):
            names.append(os.path.basename(path))
            try:
                with open(path, encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
            except (OSError, SyntaxError):
                continue
            names += [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        return list(dict.fromkeys(names))[:20]

    def describe(self) -> str:
        """Compact text for the voice agent's system prompt."""
        p = self.profile
        lines = [
            f"Career {p.career}, lab day {p.lab_day}. Bond {p.bond}/100 ({p.title}).",
            "Chapters: " + "; ".join(
                f"{c.id} {c.title} [{c.attribute.value}] {'cleared' if c.id in p.chapters_cleared else 'open'}"
                for c in CHAPTERS),
            "Mastery: " + ", ".join(f"{c.concept_title} {p.concept(c.concept).mastery}" for c in CHAPTERS),
        ]
        if p.due_concepts():
            lines.append("Due for review: " + ", ".join(p.due_concepts()))
        exp = self.experiment
        if exp and exp.stage != "debrief":
            lines.append(f"ACTIVE EXPERIMENT {exp.chapter.id} '{exp.chapter.title}', step: {exp.stage}. "
                         + _STAGE_GUIDE.get(exp.stage, ""))
        if self.review and self.review.answered is None:
            lines.append(f"OPEN REVIEW QUESTION {self.review.question.id}: waiting for answer_review.")
        return "\n".join(lines)


_STAGE_GUIDE = {
    "predict": "Waiting for the trainer's prediction (option letter + confidence) → submit_prediction.",
    "evidence": "Waiting for the culprit line → present_evidence.",
    "explain": "Waiting for a spoken explanation → submit_explanation (verbatim).",
    "fix": "Waiting for a treatment letter → choose_fix.",
    "reprove": "Fix applied and measured. keep_fix to finish, or choose_fix to try another.",
}


def _result_view(result: dict) -> dict:
    keep = ("metrics", "headline", "series", "notes", "calls", "audit", "graph", "loaded", "error", "wall_ms", "python")
    return {k: result[k] for k in keep if k in result}


def _option_index(option: Any, n: int) -> int:
    if isinstance(option, int) or (isinstance(option, str) and option.strip().isdigit()):
        i = int(option)
        i = i - 1 if 1 <= i <= n else i
    else:
        s = str(option or "").strip().upper()
        i = "ABCD".find(s[:1]) if s else -1
    if not 0 <= i < n:
        raise LabError(f"Pick one of {', '.join('ABCD'[:n])}.")
    return i


def _confidence(value: Any) -> int:
    if isinstance(value, int) and 1 <= value <= 3:
        return value
    s = str(value or "").strip().lower()
    for level, name in CONFIDENCE.items():
        if s.startswith(name[:4]) or s == str(level):
            return level
    if s in ("sure", "very", "high", "100", "definitely", "confident"):
        return 3
    if s in ("low", "unsure", "no idea", "random"):
        return 1
    return 2


def _static_verdict(ch: Chapter, root: str) -> str:
    """What the analyzers say about the chapter's code after a fix."""
    a = analyze_repo(root)
    if ch.slug == "leaks":
        leaks = [l for l in a.leaks if os.path.basename(l.file) == "reports.py"]
        return leaks[0].summary if leaks else "dataflow: every path out of load_report closes the file"
    if ch.slug == "frozen":
        chains = [c for c in a.blocking if os.path.basename(c.root.file) == "profiles.py"]
        return chains[0].summary if chains else "call graph: no async function reaches a blocking call"
    if ch.slug == "stampede":
        loops = [r for r in a.loops if os.path.basename(r.func.file) == "orders.py"]
        return loops[0].summary if loops else "call graph: no round trip inside a loop"
    if ch.slug == "silent":
        ev = ch.find_evidence(a, root)
        return ("a broad except still swallows errors" if ev.best else "no swallowed exceptions") + (
            "; a call has no timeout" if ev.ok else "; every call has a timeout")
    if ch.slug == "tangle":
        if a.arch.hidden_cycles:
            return "module graph: cycle billing ↔ orders still exists, hidden in a function-level import"
        if a.arch.cycles:
            return "module graph: cycle " + " ↔ ".join(a.arch.cycles[0])
        return "module graph: acyclic"
    return ""

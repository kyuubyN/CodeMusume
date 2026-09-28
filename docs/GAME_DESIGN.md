# CodeMusume — Game design

CodeMusume is a raising sim where the thing you raise is a codebase, and the
thing that actually grows is you. Dr. Agnes Tachyon does not lecture: she runs
experiments on real code, makes you commit to a prediction, measures what
really happens, and then makes you explain it out loud.

This document records the research behind that loop and how each finding
turned into a mechanic.

## 1. Research

### What people learning software architecture say is missing

- **No feedback loop.** The consequences of a design decision show up months
  or years later, often after you have left the team. Practitioners on
  [Ask HN: How to learn software architecture?](https://news.ycombinator.com/item?id=30913173)
  describe it as "the key to good design is experience, the key to experience
  is bad design" and say you have to stay 2–3 years somewhere to see your own
  decisions age.
- **Books are abstract, examples are toys or Big-Tech scale.** Patterns are
  learned as vocabulary, disconnected from the code people actually own.
- **Hidden complexity only shows up under load or failure.** Leaks, stalls and
  cascades are invisible in code review; you find them through incidents.
- **What helped them:** reading real codebases asking "what fails if X
  breaks?", prototypes to test a claim, and kata-style practice where you
  argue trade-offs and get feedback
  ([architectural katas](https://dl.acm.org/doi/fullHtml/10.1145/3593663.3593694)).
- **Fitness functions** ([Building Evolutionary Architectures](https://www.oreilly.com/library/view/building-evolutionary-architectures/9781491986356/ch02.html))
  are the professional answer: turn an architectural quality into something a
  program can measure.

### Why a generic AI tutor is not enough

- In a ~1,000-student field experiment, students with plain GPT-4 did better
  during practice and **worse** once it was taken away; a tutor prompted to
  withhold answers and give hints removed most of the harm
  ([Bastani et al., "Generative AI can harm learning", PNAS 2025](https://scale.stanford.edu/publications/generative-ai-can-harm-learning)).
  An assistant that answers becomes a crutch.
- **Prediction beats studying.** Committing to a prediction and getting it
  wrong produces a prediction error that strengthens memory
  ([predictive learning account of the testing effect, PNAS](https://www.pnas.org/doi/10.1073/pnas.2506530122);
  [Predicting as a learning strategy](https://pmc.ncbi.nlm.nih.gov/articles/PMC8642250/)).
  The **hypercorrection effect**: errors made with *high confidence* are the
  ones most likely to be corrected.

### How visual novels teach

- A survey of 31 educational VNs found five strategies: teaching through
  **choice**, **scripted sequences**, **mini-games**, **exploration**, and
  non-interactive exposition
  ([Camingue, Melcer & Carstensdottir, FDG '20](https://dl.acm.org/doi/10.1145/3402942.3403004)).
- A study of static vs LLM-driven educational narratives found that players
  want **responsive feedback on their progress**, **choices with visible
  consequences**, and some **silly options**; the biggest frustration was
  hub-and-spoke loops that send you back to repeat dialogue until you say the
  right thing ([arXiv 2505.08891](https://arxiv.org/html/2505.08891)).
- **Ace Attorney** teaches reasoning with two verbs: *press* a statement and
  *present* the evidence that contradicts it. Victories feel earned because
  the player makes the deduction, not the character.

### How Uma Musume keeps you training

- **Career mode is a roguelite**: a fixed number of turns (72 + finale), each
  one a choice between training, resting, racing; energy drives failure rate;
  mood multiplies gains ([career mode](https://umamusu.wiki/Game:Career_Mode)).
- **Goal races** can end the run early, so every turn has stakes.
- **Friendship training**: training alongside a support character raises the
  bond; a maxed bond turns that facility "rainbow" with big bonuses.
- **Legacy / Sparks**: a finished trainee becomes a *parent*; her sparks are
  inherited by the next trainee as stat and skill boosts
  ([legacy guide](https://game8.co/games/Umamusume-Pretty-Derby/archives/536822)).
  Every run makes the next one stronger, so a loss is still progress.
- Players say the hook is not the gacha but *the victory that keeps eluding
  you* and wanting to try a better build.

## 2. Design pillars

| Finding | Mechanic |
|---|---|
| Architecture has no feedback loop | **The harness compresses years into seconds**: every claim is measured on running code (fd leaks, event-loop lag, query counts, p99 under chaos, blast radius). |
| Generic AI answers → crutch | **Agnes never answers first.** She asks you to predict, present evidence and explain; hints cost energy. |
| Prediction error + hypercorrection | **Bet with confidence** (guess / likely / certain). Certain-and-wrong is called out and remembered. |
| Ace Attorney *present evidence* | **Present the culprit line.** The accepted lines come from the static analyzers (CFG, call graph, import graph), not from a script. |
| Explaining aloud (voice) | **Explain phase**: you explain *why* out loud; a rubric of key ideas grades it and Agnes follows up on what you missed. |
| VN choices with consequences, no hub loops | **Fix choice** among real patches, including plausible wrong ones. A wrong fix is applied and *measured*, so you see why it failed; you can revert and try again with new information instead of repeating dialogue. |
| Silly options | Every prediction has one Agnes-flavoured absurd option. |
| Uma career, energy, mood | **Career of 12 turns** with experiments, reviews, rest, and the Derby finale. |
| Friendship training | **Bond** with Agnes: Test Subject → Lab Assistant → Research Partner → Co-author. From Partner up, experiments can trigger **Eureka** (x1.5 rewards). |
| Legacy / sparks | Finished careers enter the **Hall of Fame** and leave **sparks** per mastered concept; sparks become Derby skills in the next career, and your best run becomes the ghost you race. |
| Spaced repetition | **Mastery map** with Leitner boxes; concepts come due for **review**, and Agnes ambushes you with a transfer question on new code. |

## 3. The loop

A career trains one trainee repository (by default the bundled lab specimen,
`tachyon_lab`, which is deliberately sick in five ways). Its five stats are
**fitness functions measured on the running code**:

| Stat | Fitness function | Chapter |
|---|---|---|
| Stamina | file descriptors still open after 400 requests with 5 % bad input | 01 The Leaking Lab |
| Speed | p99 latency of 40 concurrent async requests (and event-loop lag) | 02 The Frozen Loop |
| Power | SQL round trips to render 200 orders (0.5 ms simulated RTT) | 03 The Stampede |
| Guts | p99 and silently-wrong answers against a chaos upstream | 04 Silent Failure |
| Wisdom | import cycles and blast radius in the module graph | 05 The Tangle |

Each **experiment** is six steps:

1. **Hypothesis** — Agnes shows the code and asks what will happen. Options are
   built around the *baseline measurement* on this machine.
2. **Experiment** — the harness runs; the chart reveals the truth.
3. **Evidence** — present the culprit line (validated by the analyzers).
4. **Explain** — say why. Rubric hits and misses drive her follow-up.
5. **Fix** — pick a patch; it is applied to the trainee's working copy.
6. **Re-prove** — measure again. Stat change = real improvement.

Mastery rewards the thinking (prediction, evidence, explanation, first-try
fix); stats reward the code. The Derby uses both: measured stats set the
runners' pace, mastered concepts fire as skills, and checkpoint questions are
answered by voice.

## 4. Free lab

Point the lab at your own Python repository. The scanner plus the analyzers
(interprocedural blocking, exception-path leaks, queries in loops, import
cycles, blast radius) fill the case file; Agnes walks you through it, writes
fix prompts for your coding agent, and rescans to confirm real fixes.
Dynamic experiments stay on the lab specimen: the harness never executes your
own code.

## 5. Onboarding

A guided tour runs on first launch (and from **Guide** in the top bar). It
spotlights the real interface, one element at a time: the voice dock, the
measured stats, the chapter board, the five-step loop, operations and reviews,
the Dossier, and the free lab. It is short on purpose: the first experiment is
itself the tutorial, with Agnes prompting every step.

## 6. Architecture standards for your own repository

The free lab runs ten fitness functions on a local repository, each linked to
the chapter that teaches it, so a failing check becomes "learn it in the lab,
then fix it in your code":

| # | Check | Chapter |
|---|---|---|
| 1 | Imports form no cycles (Tarjan SCC over runtime imports) | 05 |
| 2 | No cycles hidden behind function-level imports | 05 |
| 3 | No volatile hub (unstable or large module) reaches most of the codebase | 05 |
| 4 | Dependencies point toward stability (Martin's SDP) | 05 |
| 5 | Every resource closed on every path (CFG dataflow) | 01 |
| 6 | No async code reaches a blocking call (call graph) | 02 |
| 7 | No round trip per loop iteration (call graph) | 03 |
| 8 | Remote calls have deadlines, errors are not swallowed | 04 |
| 9 | No oversized module that everyone depends on | 05 |
| 10 | Public functions declare return types | 05 |

Imports inside `if TYPE_CHECKING:` and a package `__init__` re-exporting its
own submodules are not counted as cycles; retry loops (`for attempt in …`) are
not counted as N+1. Free-lab stats are scored by findings per thousand lines,
so size alone is never punished.

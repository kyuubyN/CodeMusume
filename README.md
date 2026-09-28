# CodeMusume: The Repo Trainer

<p align="center">
  <strong>A voice-first raising sim where you train a codebase, and Dr. Agnes Tachyon trains you.</strong><br>
  She never hands you the answer: she runs experiments on real code, makes you predict, measures what actually happens, and makes you explain why, out loud.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"></a>
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React 18">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/AssemblyAI-Voice_Agent_API-6B4EFF" alt="AssemblyAI Voice Agent API">
  <img src="https://img.shields.io/badge/Tests-344_passing-brightgreen" alt="Tests: 344 passing">
</p>

---

## Why

People learning software architecture keep saying the same thing: **there is no feedback loop.** The consequences of a design decision show up months later, often after you have left the team. Books are abstract, examples are toys, and a chat assistant that answers for you becomes a crutch ([Bastani et al., PNAS 2025](https://scale.stanford.edu/publications/generative-ai-can-harm-learning)).

CodeMusume compresses that loop into minutes. Every claim is **measured on running code**, and every lesson follows the pattern learning research says works: *predict → observe → explain*. The research and design decisions are in [`docs/GAME_DESIGN.md`](docs/GAME_DESIGN.md).

## How it plays

**The trainee** is `tachyon_lab`, a small service that is sick in five measurable ways. Its five stats are fitness functions measured in a sandboxed subprocess:

| Stat | Measured | Chapter |
|---|---|---|
| Stamina | file descriptors still open after 400 requests with bad input | 01 The Leaking Lab |
| Speed | p99 latency of 40 concurrent async requests, event-loop lag | 02 The Frozen Loop |
| Power | SQL round trips to render one page | 03 The Stampede |
| Guts | silently wrong totals and p99 against a chaos upstream | 04 Silent Failure |
| Wisdom | modules dragged into a unit test, import cycles | 05 The Tangle |

**An experiment** is five steps, all doable by voice:

1. **Hypothesis**: bet on the outcome with a confidence level. Options are built around the baseline measured on *your* machine. Certain-and-wrong is called out: that is the one you remember.
2. **Evidence**: point at the culprit line (Ace Attorney style). Accepted lines come from the static analyzers, not a script.
3. **Explain**: say why. A rubric of key ideas grades it; what you missed comes back as a Socratic question.
4. **Treatment**: choose a real patch. Some are plausible and wrong (`gc.collect()`, `async def` without `await`, an index for an N+1, a lazy import for a cycle), and they get measured too.
5. **Re-measure**: before and after, on real code, plus what the analyzers now say.

**A career** (Uma Musume style) is 12 turns of experiments, pop-quiz reviews and rest, ending in the **Grand Derby**, a benchmark race on your measured stats against your best past career's ghost. What carries over: **mastery** per concept with spaced repetition (Leitner boxes), your **bond** with Agnes (titles, Eureka ×1.5), prediction **calibration**, the **Hall of Fame**, and **sparks** that become Derby skills.

**The free lab** points the same engine at your own Python repository: ten architecture checks, each linked to the chapter that teaches it, plus a case file with fix prompts for your coding agent. Your code is only analyzed statically, never executed.

A guided tour opens on first launch (reopen it with **Guide**).

## The engine (written from scratch)

| Piece | What it does | Where |
|---|---|---|
| CFG builder | statement-level control-flow graphs with exceptional edges; `finally` duplicated per exit path | `backend/app/lab/analysis/cfg.py` |
| Resource dataflow | forward "may be open" analysis; finds leaks on exception paths and names the raising line | `analysis/dataflow.py` |
| Call graph | whole-repo symbol table resolved through imports (relative, `src/` layouts, packages); blocking-call reachability from `async def`; round trips per loop iteration | `analysis/callgraph.py` |
| Module graph | Tarjan SCC cycles, hidden (lazy) cycles, `TYPE_CHECKING`-only and facade edges, Martin's Ca/Ce/instability, blast radius | `analysis/archgraph.py` |
| Measurement harness | subprocess probe with `/proc/self/fd`, `sys.addaudithook` (PEP 578), `sys.monitoring` (PEP 669), event-loop lag sentinel, sqlite trace, in-process chaos HTTP server | `backend/app/lab/harness/` |
| Standards check | ten fitness functions with evidence; density-scored stats | `backend/app/lab/standards.py` |

The analyzers were validated on httpx, fastapi, starlette, mcp and pydantic, and on this repository (they found a real leaked sqlite connection in our own harness).

## Voice: AssemblyAI Voice Agent API

The browser opens the Voice Agent WebSocket directly with a short-lived token minted by the backend. Mic audio goes in as 24 kHz PCM16 through an AudioWorklet; Agnes's voice plays back with barge-in. The agent drives the whole game through **20 tools** (`start_experiment`, `submit_prediction`, `present_evidence`, `submit_explanation`, `choose_fix`, `architecture_report`, …). Every tool result carries a `say` hint for the next step, and the system prompt is refreshed with live state as the game changes. Session keyterms include the trainee's file and function names, so "fetch profile" and "N plus one" are recognized.

Every action also has a button, so the game is fully playable without a microphone or an API key.

## Quickstart

Prerequisites: Python 3.12+, Node.js 18+.

```bash
git clone git@github.com:kyuubyN/CodeMusume.git
cd CodeMusume
cp .env.example .env    # add ASSEMBLYAI_API_KEY for voice
```

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app --port 8000
```

Frontend, in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

`TARGET_REPO_PATH=lab` (default) starts a career on the lab specimen; set it to a path to start in the free lab on that repo. Your profile and the trainee's working copy live in `backend/.lab/` (gitignored); delete it to start over.

## Tests

```bash
cd backend && pytest -q        # 344 tests: analyzers, harness, experiments, careers, voice tools
cd frontend && npm run build
```

## History

CodeMusume started at the IBM Bob 2.0 hackathon (session logs in [`bob_sessions/`](bob_sessions/SUMMARY.md)) and was rebuilt for the AssemblyAI voice agent hackathon around the measured-experiment loop.

## License

Apache License 2.0, see [LICENSE](LICENSE).

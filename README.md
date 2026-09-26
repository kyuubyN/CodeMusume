# CodeMusume: The Repo Trainer


<p align="center">
  <strong>Transforming cold static code analysis into a high-stakes, gamified development experience inspired by <em>Uma Musume: Pretty Derby</em>.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React 18">
  <img src="https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white" alt="Vite 5">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/IBM_Bob-2.0_Powered-1261FE?logo=ibm&logoColor=white" alt="IBM Bob 2.0">
  <img src="https://img.shields.io/badge/Tests-312_Passing-brightgreen" alt="Tests: 312 Passing">
</p>

---

##  The Vision

In modern software engineering, codebases suffer from **Architecture Drift**, silent technical debt, and creeping performance bottlenecks. Yet traditional linting, profiling, and static analysis reports often feel like tedious chores—developers ignore warnings until production outages occur.

**CodeMusume** transforms any repository into an elite **Trainee**. 

Under the sharp, eccentric guidance of **Dr. Agnes Tachyon** (Chief Enterprise Architect) and powered by **IBM Bob 2.0** as your autonomous refactoring engine with **Featherless AI** providing live play-by-play commentary, you train, refactor, and race your code against grueling real-world production stress tests!

---

##  The 5 Core Code Attributes

CodeMusume's AST scanner parses the repository and maps code quality metrics directly to the 5 classic Uma Musume attributes:

| Attribute | Meaning | Real Repo Metric | Bob's Training Focus |
| :--- | :--- | :--- | :--- |
| **🏃 Speed (スピード)** | Response Latency & Build Time | AST complexity & synchronous blocking I/O | Async refactoring (`asyncio`, `httpx.AsyncClient`) |
| **🔋 Stamina (スタミナ)** | Memory & Leak Resistance | Resource handle lifetimes & allocations | Context managers (`with`/`async with`) & connection pooling |
| **💥 Power (パワー)** | Throughput & Concurrency | Batching logic & parallelism | Concurrency primitives (`asyncio.gather`, batching) |
| **❤️ Guts (根性)** | Resilience & Error Recovery | Exception boundaries & retry logic | Circuit breakers, typed errors & explicit timeouts |
| **🧠 Wisdom (賢さ)** | Architecture & Test Coverage | Metamodel compliance & test ratio | Strict PEP 484 typing & modular DDD boundaries |

---

##  Key Features

- **🔬 Python AST Code Smell Scanner**: Deep static inspection extracting cyclomatic complexity, resource lifetimes, unhandled bare exceptions, and type hints.
- **👩‍🔬 Dr. Agnes Tachyon Persona**: Mad-scientist persona with authentic Japanese vocalizations (Kokoro TTS / Featherless Cloud API) and bilingual English enterprise subtitles.
- **🌐 Real-Time DuckDuckGo MCP Research**: During training, Agnes dispatches autonomous research queries to fetch modern architectural best practices and updates the knowledge base.
- **🏁 10-Interaction Qualification Cycle & Grand Derby**: Engage in 10 training and chat interactions with Dr. Agnes to qualify for the **2,000m Grand Derby**.
- **📝 Interactive Architecture Checkpoint Exam**: Mid-race quiz testing real-world architectural scenarios. Wrong answers slow your trainee down in real time!
- **🎮 Real-Time 2D Canvas Race Simulator**: 100-tick physics simulation featuring dynamic obstacle events (*Memory Leak Surge*, *Lock Contention*, *Spurious Timeout*) and live Jikkyou race commentary.
- **🎵 Dynamic Soundtrack & Audio Ducking**: Continuous BGM (`Steady Steps.mp3`) with automatic volume ducking while speech synthesis is active.
- **🛡️ 0.0 MB Local VRAM Guardrail**: Built to run smoothly even on legacy hardware (e.g. AMD Radeon HD 5450 2GB VRAM) via remote cloud inference or lightweight CPU fallback.

---

##  Architecture

```
[ Frontend: React 18 + Vite + Tailwind CSS + Canvas 2D ]
         │ (REST / Server-Sent Events / Web Audio)
         ▼
[ Backend: FastAPI Engine ]
    ├── Python AST & Metric Scanner
    ├── Turn-Based Training State Machine
    ├── DuckDuckGo MCP Research Service
    ├── Architecture Checkpoint Quiz Service
    ├── Real-Time Race Tick Simulator (100 ticks / 2,000m)
    └── AI Gateways
         ├── IBM Bob 2.0 (Surgical Refactoring Engine & bob_sessions)
         ├── Featherless AI (DeepSeek-V4.1-Flash LLM)
         └── Tachyon Voice Engine (Kokoro-82M / jf_nezumi)
```

---

##  IBM Bob 2.0 Integration

IBM Bob 2.0 plays a dual role in CodeMusume:
1. **Platform Engineering**: Bob designed and implemented the full-stack architecture across 7 verified development missions, tracked in [`bob_sessions/SUMMARY.md`](bob_sessions/SUMMARY.md), backed by 312 automated unit tests.
2. **In-Game Surgical Refactoring Engine**: When code smells are diagnosed, CodeMusume generates token-efficient (< 800 tokens) surgical prompts specifically tailored for IBM Bob (`trainer_service.py:generate_bob_prompt()`), elevating codebases from **Rank E (350)** to **Rank S/SS (800+)**.

---

##  Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- (Optional) Featherless AI API key for cloud LLM and TTS

### 1. Clone & Environment Configuration

```bash
git clone git@github.com:kyuubyN/CodeMusume.git
cd CodeMusume
cp .env.example .env
```

Edit `.env` to configure your keys:
```env
FEATHERLESS_API_KEY=your_featherless_api_key_here
FEATHERLESS_MODEL=deepseek-ai/DeepSeek-V4.1-Flash
TARGET_REPO_PATH=./sample_trainee_repo
```

### 2. Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

##  Testing

Run the full backend test suite (312 tests covering schemas, AST scanner, training state machine, race simulation, quiz, and voice engine):

```bash
cd backend
pytest tests/ -v
```

Build the frontend:
```bash
cd frontend
npm run build
```

---

##  License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.

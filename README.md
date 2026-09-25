# 🏇 CodeMusume: The Repo Trainer (Powered by IBM Bob 2.0 & Featherless AI)

> **Official Entry for the IBM Bob 2.0 Hackathon (lablab.ai)**  
> *Transforming cold static analysis into a high-stakes, gamified development experience inspired by Uma Musume: Pretty Derby.*

---

## 🌟 The Vision

In modern software development, codebases suffer from **Architecture Drift**, technical debt, and silent performance bottlenecks. While developers often view linting, profiling, and testing as boring chores, **CodeMusume** turns any repository into a **Trainee**.

With **IBM Bob 2.0** as your Head Coach and **Featherless AI** as your high-energy Race Commentator, you analyze, train, refactor, and race your code against real-world production stress tests!

---

## 📊 The 5 Core Code Attributes

| Attribute | Meaning | Real Repo Metric | Bob's Training Focus |
| :--- | :--- | :--- | :--- |
| **🏃 Speed (スピード)** | Response Latency & Build Time | AST complexity & import tree depth | Async refactoring & hot-path optimization |
| **🔋 Stamina (スタミナ)** | Memory & Leak Resistance | Resource handle lifetimes & allocations | Connection pooling & memory guards |
| **💥 Power (パワー)** | Throughput & Concurrency | Batching logic & parallelism | Concurrency primitives & query indexing |
| **❤️ Guts (根性)** | Resilience & Error Recovery | Exception boundaries & retry logic | Circuit breakers & graceful degradation |
| **🧠 Wisdom (賢さ)** | Architecture & Test Coverage | Metamodel compliance & test ratio | Strict typing & comprehensive unit tests |

---

## 🏗️ Architecture

```
[ Frontend: React + Vite + Canvas 2D ]
         │ (REST / SSE Events)
         ▼
[ Backend: FastAPI Engine ]
    ├── AST & Metric Scanner
    ├── Turn-based Training State Machine
    ├── Race Tick Simulator
    └── AI Gateways
         ├── IBM Bob 2.0 (Repo Transformations & bob_sessions)
         └── Featherless AI (Live Jikkyou Race Commentary)
```

---

## 🚀 Quickstart

### 1. Environment Setup
Fill in your `FEATHERLESS_API_KEY` in `.env`:
```bash
cp .env.example .env
```

### 2. Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🏆 Hackathon Traceability
All development sessions executed by **IBM Bob 2.0** are recorded in the [`bob_sessions/`](./bob_sessions/) directory as required by lablab.ai.

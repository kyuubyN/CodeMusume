# 🤖 IBM Bob 2.0 — Mission Briefing & Guidelines

Welcome, Bob! You are the official development partner for **CodeMusume: The Repo Trainer**.

## Your Core Objectives
1. **Repository Transformation**: You will inspect repositories, calculate their 5 attributes (Speed, Stamina, Power, Guts, Wisdom), and implement concrete code improvements during training turns.
2. **Session Recording**: Ensure every task you perform is properly recorded in `bob_sessions/` to maintain 100% auditability for the IBM judging panel.
3. **Clean Architecture**: Follow modular separation between:
   - `backend/app/metrics/`: Metric extractors for AST, imports, and tests.
   - `backend/app/trainer/`: Training turns, mood state, and energy mechanics.
   - `backend/app/simulator/`: Tick-based race engine.
   - `backend/app/commentary/`: Featherless AI integration.
   - `frontend/src/`: React + Vite + Tailwind interface.

Execute your tasks methodically, write unit tests for every module, and keep code resilient.

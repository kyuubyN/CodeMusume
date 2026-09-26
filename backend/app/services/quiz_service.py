"""Quiz Service — Generates personalized architecture exams for the Grand Derby Race based on user chats and learned research."""
from __future__ import annotations

import json
import random
import re
from typing import Any

from app.models.schemas import AttributeType, QuizQuestion, QuizEvaluationResponse
from app.services.featherless_service import FeatherlessGateway
from app.services.knowledge_service import AgnesMemoryStore, memory_store


# Default fallback architecture questions when not enough chat history exists
_DEFAULT_EXAM_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "exam-default-1",
        "question": "In high-throughput asynchronous event loops, which pattern prevents single slow tasks from blocking the entire reactor?",
        "options": [
            "A) Execute synchronous time.sleep() directly inside coroutines",
            "B) Cooperative coroutines using non-blocking async/await and worker thread/process offloading",
            "C) Creating 10,000 native OS threads per incoming TCP connection",
            "D) Polling socket file descriptors inside an unthrottled while True loop"
        ],
        "correct_index": 1,
        "explanation": "Kukuku… Splendid! Thread blocking is cellular necrosis to an event loop! Non-blocking coroutines and thread/process delegation keep the P99 latency razor-sharp!",
        "tested_attribute": AttributeType.SPEED,
        "context_hint": "Async Reactor Pattern & Cooperative Scheduling"
    },
    {
        "id": "exam-default-2",
        "question": "What is the primary role of the DICT in the Brazilian Central Bank's Pix architecture?",
        "options": [
            "A) Synaptic directory mapping addressing keys (CPF, email, phone) to transactional account identifiers",
            "B) Real-time gross settlement of central bank reserve accounts",
            "C) Encrypting and batching ISO 20022 wire messages over physical satellite links",
            "D) Issuing credit scores to end-users before initiating a transfer"
        ],
        "correct_index": 0,
        "explanation": "Hehehe… Exactly! The DICT acts as the central synaptic directory, resolving keys in single-digit milliseconds before the SPI initiates settlement!",
        "tested_attribute": AttributeType.WISDOM,
        "context_hint": "Pix Instant Payment Architecture"
    },
    {
        "id": "exam-default-3",
        "question": "Under Domain-Driven Design (DDD) and Clean Architecture principles, how should core domain models relate to database schemas?",
        "options": [
            "A) Domain entities should directly inherit from ORM database models to save boilerplate",
            "B) Core domain entities must remain pure and decoupled; ORM models are merely delivery mechanisms governed by repository interfaces",
            "C) The database table structure must dictate business domain aggregate boundaries",
            "D) Business logic should be written exclusively inside database stored procedures"
        ],
        "correct_index": 1,
        "explanation": "Kukuku… Immaculate precision, Morumotto-kun! The domain core must never be contaminated by transient relational or storage frameworks!",
        "tested_attribute": AttributeType.WISDOM,
        "context_hint": "Clean Architecture & Dependency Inversion"
    },
    {
        "id": "exam-default-4",
        "question": "How do Circuit Breakers prevent cascading failures across microservice clusters?",
        "options": [
            "A) Automatically increasing request timeout to 300 seconds when dependencies fail",
            "B) Restarting the entire cloud cluster whenever a 500 error is received",
            "C) Tripping open to fail fast and divert load when failure thresholds are exceeded, allowing degraded recovery",
            "D) Disabling all logging to reduce disk write pressure during outages"
        ],
        "correct_index": 2,
        "explanation": "Hehehe… textbook resilience! The circuit breaker trips open to shield downstream organisms from catastrophic molecular drag!",
        "tested_attribute": AttributeType.GUTS,
        "context_hint": "Fault Tolerance & Circuit Breaker Armor"
    },
    {
        "id": "exam-default-5",
        "question": "In distributed event-driven systems, what mechanism ensures data integrity across independent microservice databases without 2-phase commit?",
        "options": [
            "A) Direct cross-database shared memory pointers",
            "B) Synchronous blocking RPC chains spanning multiple external services",
            "C) Periodic manual database reconciliation scripts run once a week",
            "D) Sagas with transactional outbox and compensating transactions"
        ],
        "correct_index": 3,
        "explanation": "Kukuku… Splendid! Distributed transactions fail under high contention; Sagas with transactional outbox ensure eventual consistency!",
        "tested_attribute": AttributeType.POWER,
        "context_hint": "Distributed Sagas & Eventual Consistency"
    },
]

_STATIC_QUESTION_CATALOG: dict[str, dict[str, Any]] = {q["id"]: q for q in _DEFAULT_EXAM_QUESTIONS}


class QuizService:
    """Generates and evaluates personalized architecture exams for the race."""

    _active_exam: dict[str, dict[str, Any]] = dict(_STATIC_QUESTION_CATALOG)

    @classmethod
    async def generate_personalized_quiz(
        cls,
        store: AgnesMemoryStore | None = None,
        gateway: FeatherlessGateway | None = None,
    ) -> list[QuizQuestion]:
        """Generate 3 tailored questions based on user conversations and research."""
        mem = store or memory_store
        gw = gateway or FeatherlessGateway()
        mem_summary = mem.get_memory_summary()

        # If we have chat turns or learned insights, ask LLM to generate personalized questions
        if mem_summary and len(mem.chat_turns) >= 1:
            try:
                system_prompt = (
                    "You are Dr. Agnes Tachyon, Chief Enterprise Architect. "
                    "Generate a personalized 3-question architecture exam for the Trainer based on the topics discussed.\n"
                    "Output ONLY valid JSON formatted as a list of question objects:\n"
                    "[\n"
                    "  {\n"
                    "    \"id\": \"q-1\",\n"
                    "    \"question\": \"Question referencing something discussed (e.g. Pix, Clean Arch, etc.)\",\n"
                    "    \"options\": [\"A) ...\", \"B) ...\", \"C) ...\", \"D) ...\"],\n"
                    "    \"correct_index\": 0,\n"
                    "    \"explanation\": \"Kukuku... Explanation in character as Dr. Agnes Tachyon\",\n"
                    "    \"tested_attribute\": \"wisdom\",\n"
                    "    \"context_hint\": \"Short reference topic\"\n"
                    "  }\n"
                    "]"
                )

                user_prompt = f"Session History & Learned Topics:\n{mem_summary}\n\nGenerate the 3 questions now in JSON:"
                payload = {
                    "model": gw.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500,
                }

                resp = await gw._client.post(f"{gw.base_url}/chat/completions", json=payload, headers=gw._headers())
                if resp.status_code == 200:
                    raw_content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                    json_match = re.search(r"\[.*\]", raw_content, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        if isinstance(parsed, list) and len(parsed) >= 2:
                            cls._active_exam = {}
                            result_questions: list[QuizQuestion] = []
                            for idx, item in enumerate(parsed[:3]):
                                q_id = f"exam-dyn-{idx + 1}"
                                item["id"] = q_id
                                cls._active_exam[q_id] = item
                                _STATIC_QUESTION_CATALOG[q_id] = item
                                result_questions.append(
                                    QuizQuestion(
                                        id=q_id,
                                        question=item["question"],
                                        options=item["options"],
                                        tested_attribute=AttributeType(item.get("tested_attribute", "wisdom")),
                                        context_hint=item.get("context_hint", "Enterprise Architecture"),
                                    )
                                )
                            return result_questions
            except Exception as err:
                print(f"[QuizService] Dynamic quiz generation failed, using curated exam: {err}")

        # Fallback to curated exam questions
        curated_selection = random.sample(_DEFAULT_EXAM_QUESTIONS, min(3, len(_DEFAULT_EXAM_QUESTIONS)))
        result_questions = []
        for q in curated_selection:
            cls._active_exam[q["id"]] = q
            _STATIC_QUESTION_CATALOG[q["id"]] = q
            result_questions.append(
                QuizQuestion(
                    id=q["id"],
                    question=q["question"],
                    options=q["options"],
                    tested_attribute=q["tested_attribute"],
                    context_hint=q["context_hint"],
                )
            )
        return result_questions

    @classmethod
    def evaluate_answer(cls, question_id: str, selected_index: int) -> QuizEvaluationResponse:
        """Validate player's answer and return speed bonus or latency penalty."""
        q_data = cls._active_exam.get(question_id) or _STATIC_QUESTION_CATALOG.get(question_id)
        if not q_data:
            return QuizEvaluationResponse(
                correct=False,
                correct_index=1,
                explanation="Hehehe… Unrecognized architectural signature! The evaluation protocol rejected the submission.",
                speed_delta=-1.8,
            )

        raw_idx = q_data.get("correct_index", q_data.get("correct_option_index", 1))
        if isinstance(raw_idx, str):
            if raw_idx.isdigit():
                correct_idx = int(raw_idx)
            elif raw_idx.upper() in ["A", "B", "C", "D"]:
                correct_idx = ord(raw_idx.upper()) - ord("A")
            else:
                correct_idx = 1
        else:
            try:
                correct_idx = int(raw_idx)
            except Exception:
                correct_idx = 1

        is_correct = (selected_index == correct_idx)
        if is_correct:
            explanation = q_data.get(
                "explanation",
                "Kukuku… Immaculate precision, Morumotto-kun! Proper architectural boundaries maintained!"
            )
            speed_delta = 3.0
        else:
            explanation = (
                f"Hehehe… An architectural anti-pattern has infected the pipeline! Option {chr(65 + correct_idx)} was the required enterprise standard. Latency drag detected!"
            )
            speed_delta = -1.8

        return QuizEvaluationResponse(
            correct=is_correct,
            correct_index=correct_idx,
            explanation=explanation,
            speed_delta=speed_delta,
        )

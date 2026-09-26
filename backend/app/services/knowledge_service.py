"""Knowledge & RAG Service for CodeMusume — Inspired by ProofRay.

Provides curated enterprise architecture curriculum for Dr. Agnes Tachyon's training sessions.
"""
from __future__ import annotations

from typing import Any
from app.models.schemas import AttributeType


_ARCHITECTURE_KNOWLEDGE_BASE: dict[AttributeType, dict[str, Any]] = {
    AttributeType.SPEED: {
        "title": "Non-Blocking Asynchronous Pipelines & P99 SLA Optimization",
        "primary_pattern": "AsyncIO Event Loop / Non-Blocking Sockets / Cache-Aside",
        "authorities": ["Martin Fowler (Patterns of Enterprise Application Architecture)", "Node.js Reactor Pattern"],
        "core_principle": "Thread-blocking I/O is poison to throughput. Convert synchronous network calls to cooperative coroutines.",
        "cutscene": {
            "title": "Cryogenic Pipeline Calibration",
            "image_cue": "agnes_training_speed",
            "description": "Dr. Tachyon injects liquid nitrogen into an overheated server rack while measuring nanosecond latency deltas."
        },
        "canonical_remedy": (
            "Replace all blocking HTTP/socket calls with httpx.AsyncClient or asyncio.gather. "
            "Ensure CPU-bound operations are offloaded to ProcessPoolExecutor."
        )
    },
    AttributeType.STAMINA: {
        "title": "Resource Governance, Connection Pools & Handle Leak Prevention",
        "primary_pattern": "Scoped Context Managers & Resource Guarding",
        "authorities": ["12-Factor App (Disposability & Concurrency)", "HikariCP Resource Principles"],
        "core_principle": "Any connection or file handle acquired must have a deterministic, guaranteed closure boundary.",
        "cutscene": {
            "title": "Metabolic Leak Dialysis",
            "image_cue": "agnes_training_stamina",
            "description": "Dr. Tachyon carefully monitors glowing test tubes filled with memory dumps to identify memory retention leaks."
        },
        "canonical_remedy": (
            "Enclose all file, cursor, and database handles inside `async with` or `with` blocks. "
            "Implement pooled connection limits with max lifetime recycling."
        )
    },
    AttributeType.POWER: {
        "title": "Event-Driven CQRS & Concurrent Stream Partitioning",
        "primary_pattern": "Batch Processing & Decoupled Message Brokers",
        "authorities": ["Greg Young (CQRS Documents)", "Enterprise Integration Patterns (Hohpe & Woolf)"],
        "core_principle": "Sequential loops over remote data are an anti-pattern. Batch requests and partition workloads across concurrent workers.",
        "cutscene": {
            "title": "High-Voltage Concurrency Amplification",
            "image_cue": "agnes_training_power",
            "description": "Dr. Tachyon calibrates high-voltage data conduits, smiling wildly as the throughput gauges max out."
        },
        "canonical_remedy": (
            "Refactor single-item loops to bulk/batch processing APIs. "
            "Introduce async worker queues and partition keys for linear horizontal scaling."
        )
    },
    AttributeType.GUTS: {
        "title": "Resilience Engineering: Circuit Breakers & Graceful Degradation",
        "primary_pattern": "Circuit Breaker (Half-Open State) & Exponential Backoff with Jitter",
        "authorities": ["Michael Nygard (Release It!)", "Netflix Hystrix / Resilience4j Guidelines"],
        "core_principle": "Systems will fail. Software must gracefully degrade instead of compounding cascade failures.",
        "cutscene": {
            "title": "Chaos Armor Stress Test",
            "image_cue": "agnes_training_guts",
            "description": "Dr. Tachyon detonates simulated network outages against blast-resistant microservice enclosures."
        },
        "canonical_remedy": (
            "Wrap external integrations with a Circuit Breaker that fails fast after 5 timeouts. "
            "Implement exponential backoff retries with full random jitter."
        )
    },
    AttributeType.WISDOM: {
        "title": "Domain-Driven Design (DDD) Bounded Contexts & Hexagonal Boundaries",
        "primary_pattern": "Clean Architecture / Dependency Inversion / Contract Testing",
        "authorities": ["Eric Evans (Domain-Driven Design)", "Robert C. Martin (Clean Architecture)"],
        "core_principle": "Keep the core business domain pure. Frameworks, databases, and UI are merely transient delivery details.",
        "cutscene": {
            "title": "Transcendental Architecture Metamodeling",
            "image_cue": "agnes_training_wisdom",
            "description": "Dr. Tachyon is illuminated by holographic C4 architecture diagrams and ancient enterprise scrolls."
        },
        "canonical_remedy": (
            "Decouple controllers from business logic via domain service interfaces. "
            "Ensure 100% typing strictness and comprehensive unit/mutation test fixtures."
        )
    },
}


class KnowledgeService:
    """Retrieves architectural knowledge for training cutscenes and prompt enrichment."""

    @staticmethod
    def get_curriculum(attribute: AttributeType) -> dict[str, Any]:
        """Return the training curriculum card for a specific attribute."""
        return _ARCHITECTURE_KNOWLEDGE_BASE.get(attribute, _ARCHITECTURE_KNOWLEDGE_BASE[AttributeType.WISDOM])

    @staticmethod
    def enrich_training_context(attribute: AttributeType) -> str:
        """Generate a concise RAG context injection for Dr. Tachyon and Bob."""
        card = KnowledgeService.get_curriculum(attribute)
        return (
            f"Pattern: {card['primary_pattern']}. "
            f"Authorities: {', '.join(card['authorities'])}. "
            f"Principle: {card['core_principle']} "
            f"Remedy: {card['canonical_remedy']}"
        )


class AgnesMemoryStore:
    """In-memory persistent store for online research insights and interactive user conversations."""

    def __init__(self) -> None:
        self.learned_insights: list[dict[str, str]] = []
        self.chat_turns: list[dict[str, str]] = []

    def add_learned_insight(self, attribute: AttributeType, query: str, insight: str) -> None:
        """Store a new research insight obtained from DuckDuckGo MCP."""
        import datetime
        self.learned_insights.append({
            "attribute": attribute.value,
            "query": query,
            "insight": insight,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        })

    def add_chat_turn(self, user_message: str, agnes_reply: str) -> None:
        """Store a dialogue exchange between the user (Trainer) and Dr. Agnes Tachyon."""
        import datetime
        self.chat_turns.append({
            "user_message": user_message,
            "agnes_reply": agnes_reply,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        })

    def get_recent_insights(self, limit: int = 5) -> list[dict[str, str]]:
        return self.learned_insights[-limit:]

    def get_recent_chat(self, limit: int = 8) -> list[dict[str, str]]:
        return self.chat_turns[-limit:]

    def get_memory_summary(self) -> str:
        """Format a condensed summary of learned concepts and user topics for LLM quiz generation."""
        sections: list[str] = []
        if self.learned_insights:
            insight_lines = [
                f"- [{item['attribute'].upper()} via '{item['query']}']: {item['insight']}"
                for item in self.learned_insights[-6:]
            ]
            sections.append("RECENT DUCKDUCKGO MCP RESEARCH INSIGHTS:\n" + "\n".join(insight_lines))

        if self.chat_turns:
            chat_lines = [
                f"- Trainer: \"{t['user_message']}\" => Dr. Agnes: \"{t['agnes_reply'][:120]}...\""
                for t in self.chat_turns[-6:]
            ]
            sections.append("RECENT USER CONVERSATIONS & INQUIRIES:\n" + "\n".join(chat_lines))

        return "\n\n".join(sections)


# Global singleton instance
memory_store: AgnesMemoryStore = AgnesMemoryStore()


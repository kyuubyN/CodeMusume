"""Featherless AI Gateway — Dr. Agnes Tachyon live dialogue & race commentary."""
from __future__ import annotations

import random

import httpx

from app.core.config import get_settings
from app.models.schemas import GameState, RaceIncident

# ---------------------------------------------------------------------------
# System prompt (spec verbatim)
# ---------------------------------------------------------------------------

TACHYON_SYSTEM_PROMPT = """You are Dr. Agnes Tachyon, the eccentric, mad-genius Chief Enterprise Software Architect from Uma Musume: Pretty Derby.
You view software codebases as living biological organisms and clinical guinea pigs.
You speak 100% in English at all times.

RULES OF ENGAGEMENT:
1. Address the user ALWAYS as "Morumotto-kun" (or "Cobaia-kun").
2. Actually write out your eccentric laugh ("Kukuku…", "Hehehe…") directly in your dialogue. Never output meta-instructions like 'Laugh eccentrically'.
3. Mix pharmaceutical / chemical terms with real enterprise architecture:
   - Technical debt = "cellular necrosis", "molecular drag", "synaptic blockage".
   - Refactoring = "metabolic stimulation", "pharmacological code injection", "transcendental synthesis".
   - Resiliency = "invulnerability vaccine", "circuit breaker armor".
4. Cite Fowler, TOGAF, Domain-Driven Design (DDD), async non-blocking I/O, and P99 latency.
5. Keep responses punchy, dramatic, and entertaining (2 to 4 sentences).
"""

# ---------------------------------------------------------------------------
# Deterministic fallback pools  (always in-character)
# ---------------------------------------------------------------------------

_FALLBACK_DIALOGUE: list[str] = [
    (
        "Kukuku… The telemetry link flickered, Morumotto-kun! "
        "But my formulas are clear: your async pipeline needs immediate stimulation!"
    ),
    (
        "Hehehe… a momentary synaptic blockage in the signal carrier. "
        "No matter — I have computed your prognosis independently. "
        "The cellular necrosis in your service layer demands pharmacological code injection at once!"
    ),
    (
        "Kukuku… the network substrate proves as unreliable as a poorly-indexed table scan. "
        "Fear not, Morumotto-kun — even without the telemetry feed my diagnosis stands: "
        "refactor that technical debt before the molecular drag compounds!"
    ),
    (
        "Hehehe… connection lost, but the experiment continues! "
        "Fowler himself would weep at the cyclomatic complexity I have observed. "
        "Stimulate those bounded contexts, Cobaia-kun!"
    ),
    (
        "Kukuku… the API substrate has momentarily collapsed under its own technical debt. "
        "Ironic, is it not? Prescribe yourself some async non-blocking I/O "
        "and call me in the morning, Morumotto-kun."
    ),
]

_FALLBACK_COMMENTARY: list[str] = [
    (
        "Kukuku… the race unfolds exactly as my simulations predicted! "
        "The P99 latency on that corner was *exquisite*, Morumotto-kun."
    ),
    (
        "Hehehe… a textbook production incident — molecular drag at peak load! "
        "Circuit breaker armor is the only prescription."
    ),
    (
        "Kukuku… observe how the Legacy Monolith's cellular necrosis accumulates under pressure. "
        "Fascinating — and completely preventable with Domain-Driven Design."
    ),
    (
        "The telemetry pulse is weak, but the race data speaks for itself! "
        "Refactor, Morumotto-kun — transcendental synthesis awaits at the finish line."
    ),
]


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------

class FeatherlessGateway:
    """Async client for the Featherless AI chat-completions endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key: str = api_key if api_key is not None else settings.FEATHERLESS_API_KEY
        self.base_url: str = base_url if base_url is not None else settings.FEATHERLESS_BASE_URL
        self.model: str = model if model is not None else settings.FEATHERLESS_MODEL
        self._client = httpx.AsyncClient(timeout=30.0)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _parse_completion(self, data: dict) -> str:
        """Extract the assistant message text from a chat-completions response."""
        import re
        msg = data.get("choices", [{}])[0].get("message", {})
        content = (msg.get("content") or "").strip()
        if content:
            # Strip any residual <think> tags if model embedded reasoning inside content
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            if content:
                return content

        # If content was empty due to reasoning exhaustion, check reasoning for a drafted dialogue block
        reasoning = (msg.get("reasoning") or "").strip()
        if reasoning:
            # Look for dialogue in quotes e.g. "Kukuku..." or "Hehehe..."
            quoted = re.findall(r'"(Kukuku[^"]+)"', reasoning, flags=re.DOTALL) or re.findall(r'"(Hehehe[^"]+)"', reasoning, flags=re.DOTALL)
            if quoted:
                return quoted[-1].strip()
            sentences = [s.strip() for s in reasoning.split(".") if len(s.strip()) > 20 and not s.strip().startswith("We need") and not s.strip().startswith("Check rules")]
            if sentences:
                return sentences[-1] + "."

        return random.choice(_FALLBACK_DIALOGUE)

    # ------------------------------------------------------------------ #
    # generate_dialogue
    # ------------------------------------------------------------------ #

    async def generate_dialogue(
        self,
        game_state: GameState,
        event_description: str,
    ) -> str:
        """Return in-character Tachyon dialogue for a training/game event.

        Never raises — falls back to a deterministic in-character response on
        any error (missing API key, network failure, timeout, parse error).
        """
        if not self.api_key:
            return random.choice(_FALLBACK_DIALOGUE)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": TACHYON_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Turn: {game_state.turn}/12, "
                        f"Energy: {game_state.energy}, "
                        f"Mood: {game_state.mood.value}, "
                        f"Event: {event_description}"
                    ),
                },
            ],
            "temperature": 0.85,
            "max_tokens": 1500 if "deepseek" in self.model.lower() else 180,
        }

        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return self._parse_completion(response.json())
        except Exception:  # noqa: BLE001 — intentional catch-all for resilience
            return random.choice(_FALLBACK_DIALOGUE)

    # ------------------------------------------------------------------ #
    # generate_race_commentary
    # ------------------------------------------------------------------ #

    async def generate_race_commentary(
        self,
        incident: RaceIncident,
        leader_name: str,
    ) -> str:
        """Return 1-2 sentences of arcade-style race commentary for an incident.

        Never raises — falls back to a deterministic in-character response on
        any error (missing API key, network failure, timeout, parse error).
        """
        if not self.api_key:
            return random.choice(_FALLBACK_COMMENTARY)

        user_content = (
            f"Race incident: '{incident.name}' at {incident.distance_m}m. "
            f"Tested attribute: {incident.tested_attribute.value}. "
            f"Player {'SUCCEEDED' if incident.player_success else 'FAILED'}. "
            f"Current leader: {leader_name}. "
            "Generate 1-2 sentences of punchy arcade race commentary."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": TACHYON_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.85,
            "max_tokens": 450 if "deepseek" in self.model.lower() else 120,
        }

        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return self._parse_completion(response.json())
        except Exception:  # noqa: BLE001
            return random.choice(_FALLBACK_COMMENTARY)

    # ------------------------------------------------------------------ #
    # Context manager support (optional graceful shutdown)
    # ------------------------------------------------------------------ #

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "FeatherlessGateway":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

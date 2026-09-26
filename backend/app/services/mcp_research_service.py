"""DuckDuckGo MCP Research Service — Live online architecture search via duckduckgo-mcp-server."""
from __future__ import annotations

import asyncio
import re
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.models.schemas import AttributeType


# Canonical search queries for training attributes (2026 enterprise focus)
ATTRIBUTE_SEARCH_QUERIES: dict[AttributeType, str] = {
    AttributeType.SPEED: "python asyncio event loop latency optimization best practices 2026",
    AttributeType.STAMINA: "python memory leak detection garbage collection tracemalloc reference cycles",
    AttributeType.POWER: "high throughput concurrency multiprocessing distributed batching python",
    AttributeType.GUTS: "circuit breaker pattern resilience chaos engineering python",
    AttributeType.WISDOM: "domain driven design event driven architecture clean architecture 2026",
}

FALLBACK_INSIGHTS: dict[AttributeType, str] = {
    AttributeType.SPEED: (
        "Recent 2026 benchmarks highlight uvloop with asyncio.gather and non-blocking sockets "
        "minimizing event-loop jitter under 100k concurrent requests."
    ),
    AttributeType.STAMINA: (
        "Modern memory hygiene prescribes weakref closures, deterministic contextlib scopes, "
        "and continuous objgraph leak tracking to prevent heap fragmentation."
    ),
    AttributeType.POWER: (
        "Distributed throughput patterns leverage chunked multiprocessing pools with zero-copy shared memory "
        "and backpressure queues to saturate multi-core processors."
    ),
    AttributeType.GUTS: (
        "Resilient systems deploy tiered circuit breakers with exponential backoff and jittered retries, "
        "ensuring downstream failure isolation without cascading thundering herds."
    ),
    AttributeType.WISDOM: (
        "DDD standards enforce aggregate boundaries, immutable domain events via transactional outboxes, "
        "and strict decoupling between business logic and transport infrastructure."
    ),
}


class McpResearchService:
    """Manages connection to duckduckgo-mcp-server and queries latest technical literature."""

    _cache: dict[str, str] = {}

    @classmethod
    async def search_duckduckgo(cls, query: str, max_results: int = 3) -> str:
        """Call duckduckgo-mcp-server via stdio MCP client and return formatted results."""
        if query in cls._cache:
            return cls._cache[query]

        server_params = StdioServerParameters(
            command="uvx",
            args=["duckduckgo-mcp-server"],
        )

        try:
            # Set 8-second timeout for the MCP tool execution
            async def _execute():
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(
                            "search",
                            arguments={"query": query, "max_results": max_results},
                        )
                        if result.content and hasattr(result.content[0], "text"):
                            return result.content[0].text
                        return ""

            raw_output = await asyncio.wait_for(_execute(), timeout=8.0)
            if raw_output and len(raw_output.strip()) > 30:
                cleaned = cls._clean_snippets(raw_output)
                cls._cache[query] = cleaned
                return cleaned
        except Exception as err:
            # Non-blocking graceful degradation
            print(f"[McpResearchService] Search failed or timed out: {err}")

        return ""

    @classmethod
    def _clean_snippets(cls, text: str) -> str:
        """Clean and condense raw DuckDuckGo search output for LLM consumption."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        summaries: list[str] = []
        for line in lines:
            if line.startswith("Summary:"):
                clean_line = re.sub(r"^Summary:\s*", "", line)
                clean_line = re.sub(r"\s+", " ", clean_line)
                summaries.append(clean_line[:180])
            elif not line.startswith("URL:") and not line.startswith("Found") and len(line) > 40:
                if len(summaries) < 3:
                    summaries.append(line[:160])

        if summaries:
            return " // ".join(summaries[:2])
        return text[:250].strip()

    @classmethod
    async def research_attribute(
        cls,
        attribute: AttributeType,
        custom_topic: str | None = None,
    ) -> str:
        """Fetch real-time research for a specific training attribute or custom user topic."""
        query = (
            f"{custom_topic} enterprise architecture python 2026"
            if custom_topic and custom_topic.strip()
            else ATTRIBUTE_SEARCH_QUERIES.get(attribute, "python enterprise architecture best practices")
        )

        search_summary = await cls.search_duckduckgo(query)
        if search_summary:
            return search_summary

        return FALLBACK_INSIGHTS.get(attribute, FALLBACK_INSIGHTS[AttributeType.WISDOM])

"""
RAG pipeline for bottleneck_analyze.

Architecture:
  1. retrieve_failures()  — query SQLite for recent execution failures
  2. embed_and_seed()     — embed failure text into ChromaDB (optional, [rag] extra)
  3. build_prompt()       — format metrics + failures into a structured LLM prompt
  4. call_llm()           — call Anthropic Claude with JSON response schema
  5. Fallback heuristic   — if no API key, return pattern-matched analysis from SQLite alone

The LLM step is optional: set ANTHROPIC_API_KEY in .env to enable it.
Without it, bottleneck_analyze returns a heuristic summary that is still
useful for identifying failure trends.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Any

from hookcli_mcp.db.models import get_db

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


async def retrieve_failures(workspace_id: str, hours: int, focus: str) -> dict[str, Any]:
    """Query SQLite for recent execution metrics and top failure traces."""
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    try:
        async with get_db() as db:
            # Aggregate metrics
            async with db.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'failed' OR status = 'dlq' THEN 1 ELSE 0 END) AS failures,
                    SUM(CASE WHEN status = 'dlq' THEN 1 ELSE 0 END) AS dlq_count,
                    AVG(
                        CASE WHEN completed_at IS NOT NULL AND started_at IS NOT NULL
                        THEN (julianday(completed_at) - julianday(started_at)) * 86400
                        ELSE NULL END
                    ) AS avg_latency_sec
                FROM executions
                WHERE started_at > ?
                """,
                (cutoff,),
            ) as cur:
                row = await cur.fetchone()

            total = row[0] or 0
            failures = row[1] or 0
            dlq_count = row[2] or 0
            avg_latency = (row[3] or 0.0) * 1000  # ms

            # Fetch top-3 recent failure traces
            focus_filter = f"%{focus}%" if focus != "all" else "%"
            async with db.execute(
                """
                SELECT hook_id, error_trace, attempt
                FROM executions
                WHERE (status = 'failed' OR status = 'dlq')
                  AND started_at > ?
                  AND (hook_id LIKE ? OR error_trace LIKE ?)
                ORDER BY started_at DESC
                LIMIT 3
                """,
                (cutoff, focus_filter, focus_filter),
            ) as cur:
                failure_rows = await cur.fetchall()

        failures_list = [
            {"hook_id": r[0], "error": (r[1] or "")[:300], "retries": r[2]}
            for r in failure_rows
        ]
    except Exception:
        # DB not yet initialized or schema missing — return empty baseline
        total = failures = dlq_count = 0
        avg_latency = 0.0
        failures_list = []

    return {
        "total_events": total,
        "failure_count": failures,
        "failure_rate_pct": round((failures / total * 100) if total > 0 else 0.0, 1),
        "dlq_count": dlq_count,
        "avg_latency_ms": round(avg_latency, 0),
        "recent_failures": failures_list,
    }


def build_prompt(metrics: dict[str, Any], hours: int, focus: str) -> str:
    failure_lines = "\n".join(
        f"  - hook={f['hook_id']}  error={f['error'][:120]}  retries={f['retries']}"
        for f in metrics["recent_failures"]
    ) or "  (no recent failures)"

    return f"""You are an AI Operations Analyst for Hook CLI MCP.
Analyze the following execution data and suggest remediation hooks.

METRICS (last {hours}h, focus="{focus}"):
  total_events:    {metrics['total_events']}
  failure_rate:    {metrics['failure_rate_pct']}%
  dlq_events:      {metrics['dlq_count']}
  avg_latency_ms:  {metrics['avg_latency_ms']}

RECENT FAILURES:
{failure_lines}

INSTRUCTIONS:
1. Identify the root cause pattern (e.g. timeout, auth expiry, payload mismatch, network flap).
2. Propose 1-3 proactive or reactive hooks using the hook_create schema.
3. Estimate impact (e.g. "Reduce MTTR by ~60%").
4. Return ONLY valid JSON — no markdown, no prose outside the object.

REQUIRED JSON SCHEMA:
{{
  "analysis": "<string — 1-2 sentence summary>",
  "root_cause": "<string — concise root cause>",
  "confidence": <float 0.0-1.0>,
  "suggested_hooks": [
    {{
      "name": "<string>",
      "source": "webhook|cron|mq",
      "filter_expr": "<jq expression>",
      "command": "<CLI command with {{{{event.*}}}} templates>",
      "expected_impact": "<string>"
    }}
  ],
  "next_steps": ["<string>"]
}}"""


def _heuristic_analysis(metrics: dict[str, Any], focus: str) -> dict[str, Any]:
    """Fast pattern-match when no LLM key is configured."""
    failure_rate = metrics["failure_rate_pct"]
    dlq = metrics["dlq_count"]

    if failure_rate == 0.0 and dlq == 0:
        return {
            "analysis": f"No failures detected in the analysis window (focus={focus!r}).",
            "root_cause": "N/A",
            "confidence": 0.95,
            "suggested_hooks": [],
            "next_steps": ["Increase time_range_hours if you expect failures."],
        }

    confidence = min(0.5 + (failure_rate / 100) * 0.4, 0.85)
    errors = " | ".join(f["error"][:60] for f in metrics["recent_failures"] if f["error"])

    return {
        "analysis": (
            f"{failure_rate}% failure rate over the window "
            f"({metrics['failure_count']}/{metrics['total_events']} events, {dlq} in DLQ). "
            f"Top errors: {errors or 'see execution logs'}."
        ),
        "root_cause": "Pattern requires LLM analysis — set ANTHROPIC_API_KEY for full diagnosis.",
        "confidence": confidence,
        "suggested_hooks": [],
        "next_steps": [
            "Set ANTHROPIC_API_KEY in .env for AI-powered root cause analysis.",
            f"Inspect DLQ: {dlq} events require manual review.",
        ],
    }


async def analyze(workspace_id: str, hours: int, focus: str) -> dict[str, Any]:
    """Full RAG pipeline: retrieve → prompt → LLM (or heuristic fallback)."""
    metrics = await retrieve_failures(workspace_id, hours, focus)

    if not ANTHROPIC_API_KEY:
        return _heuristic_analysis(metrics, focus)

    # Cache key — avoid calling LLM twice for identical inputs in the same window
    cache_key = hashlib.sha256(
        f"{workspace_id}:{hours}:{focus}:{metrics['failure_count']}".encode()
    ).hexdigest()[:16]

    try:
        from hookcli_mcp.services.queue import cache_get, cache_set

        cached = await cache_get(f"bottleneck:{cache_key}")
        if cached:
            return cached
    except Exception:
        cached = None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": build_prompt(metrics, hours, focus)}],
        )
        raw = message.content[0].text.strip()
        # Strip any accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
    except Exception as exc:
        result = _heuristic_analysis(metrics, focus)
        result["next_steps"].append(f"LLM call failed: {type(exc).__name__}: {exc}")

    try:
        await cache_set(f"bottleneck:{cache_key}", result, ttl_seconds=900)
    except Exception:
        pass

    return result

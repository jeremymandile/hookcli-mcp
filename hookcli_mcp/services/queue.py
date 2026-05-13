"""Redis-backed volatile state: retry queues, rate limits, task distribution.

Boundary contract:
  - Durable state  → SQLite (hooks config, execution logs, audit trail)
  - Volatile state → Redis (retry queues, approval events, caching, rate limits)
  - Vector store   → ChromaDB (bottleneck_analyze embeddings)

Never write authoritative hook config or audit records to Redis.
"""

import json
import os
from typing import Any

import redis.asyncio as aioredis

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Module-level connection pool — created lazily on first use.
_pool: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(_REDIS_URL, decode_responses=True)
    return _pool


async def push_retry(hook_id: str, event_id: str, payload: dict[str, Any], attempt: int = 1) -> None:
    """Queue a failed event for retry. Worker pops from the left (FIFO)."""
    conn = _get_redis()
    message = json.dumps({"hook_id": hook_id, "event_id": event_id, "payload": payload, "attempt": attempt})
    await conn.rpush("hookcli:retry_queue", message)


async def pop_retry(timeout: int = 5) -> dict[str, Any] | None:
    """Block-pop the next retry message. Returns None on timeout."""
    conn = _get_redis()
    result = await conn.blpop("hookcli:retry_queue", timeout=timeout)
    if result:
        _, raw = result
        return json.loads(raw)
    return None


async def push_dlq(hook_id: str, event_id: str, payload: dict[str, Any], error: str) -> None:
    """Move a permanently failed event to the dead-letter queue."""
    conn = _get_redis()
    message = json.dumps({"hook_id": hook_id, "event_id": event_id, "payload": payload, "error": error})
    await conn.rpush("hookcli:dlq", message)


async def cache_set(key: str, value: Any, ttl_seconds: int = 900) -> None:
    """Cache a JSON-serialisable value with TTL (default 15 min)."""
    conn = _get_redis()
    await conn.setex(f"hookcli:cache:{key}", ttl_seconds, json.dumps(value))


async def cache_get(key: str) -> Any | None:
    """Retrieve a cached value. Returns None on miss or expiry."""
    conn = _get_redis()
    raw = await conn.get(f"hookcli:cache:{key}")
    return json.loads(raw) if raw is not None else None

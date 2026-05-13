import aiosqlite
from contextlib import asynccontextmanager

DB_PATH = "./hooks.db"


@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL")
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    async with get_db() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS hooks (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                name TEXT NOT NULL,
                config JSON NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                hook_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                status TEXT,
                attempt INTEGER DEFAULT 1,
                payload_hash TEXT NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                output TEXT,
                error_trace TEXT
            );
            CREATE TABLE IF NOT EXISTS dlq (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                raw_event JSON NOT NULL,
                last_error TEXT NOT NULL,
                failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                key_hash TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'operator',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                details JSON,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()

import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _allowed_roles(min_role: str) -> list:
    hierarchy = {"viewer": 0, "operator": 1, "admin": 2}
    return [r for r, lvl in hierarchy.items() if lvl >= hierarchy.get(min_role, 0)]


async def get_current_context(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    # MVP: hardcoded test key. Replace with DB lookup in production.
    if key_hash == hashlib.sha256("admin-test-key".encode()).hexdigest():
        return {"workspace_id": "default", "role": "admin"}
    raise HTTPException(status_code=401, detail="Invalid API key")


def require_role(required_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ctx = kwargs.get("context")
            if not ctx:
                raise HTTPException(status_code=403, detail="No context provided")
            if ctx.get("role") not in _allowed_roles(required_role):
                raise HTTPException(status_code=403, detail=f"Requires {required_role} role")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def generate_api_key(workspace_id: str, role: str, ttl_hours: int = 720) -> str:
    raw_key = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=ttl_hours)
    # Store in DB in production
    return raw_key

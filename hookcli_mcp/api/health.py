from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    docker_daemon: bool
    sqlite_conn: bool


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    import aiosqlite
    import docker

    try:
        docker.from_env().ping()
        docker_ok = True
    except Exception:
        docker_ok = False
    try:
        async with aiosqlite.connect(":memory:") as db:
            await db.execute("SELECT 1")
        sqlite_ok = True
    except Exception:
        sqlite_ok = False
    return HealthResponse(
        status="healthy" if (docker_ok and sqlite_ok) else "degraded", docker_daemon=docker_ok, sqlite_conn=sqlite_ok
    )

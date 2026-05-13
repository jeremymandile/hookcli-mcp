from typing import Any

from pydantic import BaseModel, Field


class BottleneckRequest(BaseModel):
    time_range_hours: int = Field(default=24, ge=1, le=168)
    focus: str = Field(default="all")
    workspace_id: str


class BottleneckResponse(BaseModel):
    analysis: str
    root_cause: str
    confidence: float
    suggested_hooks: list[dict[str, Any]]
    next_steps: list[str]


async def bottleneck_analyze(req: BottleneckRequest) -> BottleneckResponse:
    """Analyze recent execution failures and suggest remediation hooks.

    Uses the RAG pipeline (SQLite metrics + optional Anthropic LLM).
    Set ANTHROPIC_API_KEY in .env for AI-powered root cause analysis;
    falls back to a heuristic summary when the key is absent.
    """
    from hookcli_mcp.services.rag import analyze

    result = await analyze(req.workspace_id, req.time_range_hours, req.focus)
    return BottleneckResponse(**result)

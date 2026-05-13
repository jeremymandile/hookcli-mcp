import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from hookcli_mcp.api import tasks, health, metrics, approvals
from hookcli_mcp.observability.otel import init_otel

init_otel()

# ── MCP Server (stdio for AI clients, /mcp for HTTP fallback) ─────────────────
mcp = FastMCP("hookcli-mcp")

# Register MCP tools by wrapping the underlying async logic directly.
# FastAPI routers handle HTTP; MCP tools handle stdio/AI invocation.
from hookcli_mcp.tools.validate import hook_validate as _http_validate, ValidateRequest
from hookcli_mcp.tools.bottleneck_analyze import bottleneck_analyze as _bottleneck_analyze, BottleneckRequest


@mcp.tool()
async def hook_validate(
    command: str,
    payload: dict = {},
    secrets: dict = {},
    timeout_sec: int = 30,
) -> dict:
    """Validate a hook CLI command against a synthetic payload in a no-network sandbox."""
    req = ValidateRequest(command=command, payload=payload, secrets=secrets, timeout_sec=timeout_sec)
    result = await _http_validate(req)
    return result.model_dump()


@mcp.tool()
async def bottleneck_analyze(
    workspace_id: str,
    time_range_hours: int = 24,
    focus: str = "all",
) -> dict:
    """Analyze recent execution failures and suggest remediation hooks."""
    req = BottleneckRequest(workspace_id=workspace_id, time_range_hours=time_range_hours, focus=focus)
    result = await _bottleneck_analyze(req)
    return result.model_dump()


# ── FastAPI (webhooks, SSE, health, Prometheus metrics) ──────────────────────
app = FastAPI(title="Hook CLI MCP Server", version="0.1.0")
app.include_router(tasks.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")

# Mount MCP over HTTP at /mcp so proxies and browser clients can reach tools
# without a stdio process. Primary AI client transport is still stdio.
app.mount("/mcp", mcp.streamable_http_app())


def http_main():
    """Entry point for `hookcli-mcp-http` — boots the webhook/SSE/metrics server."""
    uvicorn.run("hookcli_mcp.server:app", host="0.0.0.0", port=8000, log_level="info")


def stdio_main():
    """Entry point for `hookcli-mcp-stdio` — runs the MCP stdio loop for AI clients."""
    mcp.run(transport="stdio")

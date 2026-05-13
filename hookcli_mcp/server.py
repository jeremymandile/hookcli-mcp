import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from hookcli_mcp.api import tasks, health, metrics, approvals
from hookcli_mcp.tools.validate import router as validate_router
from hookcli_mcp.observability.otel import init_otel


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_otel(app)
    yield


app = FastAPI(
    title="Hook CLI MCP Server",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(tasks.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(validate_router, prefix="/api/tools/validate")


def main():
    uvicorn.run("hookcli_mcp.server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()

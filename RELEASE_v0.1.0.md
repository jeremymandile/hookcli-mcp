# Hook CLI MCP v0.1.0 Release Notes

## Overview

v0.1.0 delivers a production-grade, AI-driven event automation server. Built on FastAPI + MCP stdio, it enables AI agents to listen to webhooks, validate CLI commands in hardened sandboxes, request human approval for high-risk actions, and self-optimize via bottleneck analysis.

## What's Included

- FastAPI server with async SSE streaming
- MCP stdio transport with `mcp dev .` discovery
- Docker/seccomp sandboxed CLI executor
- `hook_validate` dry-run (template, schema, security, sandbox)
- Human-in-the-loop approval flow (Slack/Teams)
- RBAC (viewer/operator/admin) + audit log
- OpenTelemetry traces + Prometheus metrics
- GitHub Actions CI pipeline

## Deployment

```bash
git clone https://github.com/your-org/hookcli-mcp.git
cd hookcli-mcp && cp .env.example .env
docker compose up -d
curl http://localhost:8000/api/health
mcp dev .
```

## Breaking Changes

- Python < 3.12 not supported
- MCP transport defaults to `stdio`
- Secrets must use `{{secret:NAME}}` syntax

## Migration Notes

- Replace in-memory `task_registry` with Redis for production scaling
- Set `OTEL_EXPORTER_OTLP_ENDPOINT` and `REDIS_URL` in `.env`

---
**Hook CLI MCP v0.1.0** — Ship safely.

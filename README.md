# Hook CLI MCP

**Advanced Event-Hook Automation Server for AI-Driven Business Process Remediation**

Hook CLI MCP gives AI assistants the power to listen to real-time business events and execute trusted CLI commands inside hardened sandboxes. Connect your Stripe webhooks, Jira tickets, CI pipelines, and support queues directly to the AI.

## Features

- **Event-Driven Automation** — Webhooks, cron, MQ triggers
- **Security-by-Design** — Docker/seccomp sandboxing, regex guards, secret masking
- **`hook_validate` Dry-Run** — Safe command testing before deployment
- **AI Bottleneck Analysis** — RAG pipeline over execution history
- **Human-in-the-Loop** — Slack/Teams approval for high-risk actions
- **Full Observability** — OpenTelemetry, Prometheus, Jaeger
- **RBAC & Audit** — Workspace-scoped roles, immutable audit trail

## Quick Start

```bash
cp .env.example .env
docker compose up -d
curl http://localhost:8000/api/health
```

## MCP Setup

```bash
pip install mcp
mcp dev .
```

Add to `mcp.json` for Claude Desktop / Cursor:

```json
{
  "mcpServers": {
    "hookcli-mcp": {
      "command": "uv",
      "args": ["run", "hookcli-mcp"]
    }
  }
}
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest tests/ -v --asyncio-mode=auto
ruff check .
```

## Architecture

```
AI Client (Claude) ──MCP──► Hook CLI MCP Server
                               ├── hook_validate (sandboxed dry-run)
                               ├── hook_create (webhook/cron/mq)
                               ├── bottleneck_analyze (RAG)
                               └── request_approval (Slack HITL)
                                        │
                               Docker Sandbox (seccomp, no-network, cap-drop)
                                        │
                               OTel ──► Jaeger / Prometheus
```

## License

MIT

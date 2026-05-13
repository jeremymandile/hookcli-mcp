# Contributing to Hook CLI MCP

Thank you for considering a contribution!

## Development Setup

```bash
git clone https://github.com/your-org/hookcli-mcp.git
cd hookcli-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Testing

```bash
pytest tests/ -v --asyncio-mode=auto   # full suite
pytest tests/security/ -v              # security tests only
ruff check .                           # lint
bandit -r hookcli_mcp/ -ll             # SAST
```

## Project Structure

```
hookcli_mcp/
├── api/          # FastAPI routers
├── auth/         # RBAC
├── core/         # Validator, approval state machine
├── db/           # SQLite models
├── observability/# OTel + Prometheus
├── sandbox/      # Docker execution
├── services/     # Slack integration
└── tools/        # MCP tool implementations
```

## Pull Request Process

1. Fork and create a feature branch
2. Ensure tests and lint pass
3. Update `CHANGELOG.md`
4. Open PR against `main`

## Reporting Issues

- Bugs: open a GitHub issue
- Security: email security@hookcli.dev (do not open public issues)

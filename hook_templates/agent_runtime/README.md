# Agent Runtime Event Hooks

These templates wire Hook CLI MCP into the **agent's own lifecycle** — startup,
message processing, command execution, and shutdown. They complement the
business-event templates (Stripe, GitHub, etc.) by governing the AI's behavior,
not just its effect on the world.

## Architecture

```
Agent Runtime (OpenClaw / Claude Code / custom gateway)
  │
  ├── gateway:startup       → verify Docker socket, load config
  ├── message:received      → content safety, audit logging
  ├── command:new           → validate before execution (hook_validate)
  ├── session:compact:after → external memory write
  ├── gateway:shutdown      → flush metrics, close connections
  │
  ▼
Hook CLI MCP
  │
  └── Business Events
       ├── payment_intent.payment_failed
       ├── workflow_run.failed
       └── ...
```

## Event Taxonomy

| Phase | Event | Hook CLI MCP Action |
|-------|-------|---------------------|
| Startup | `gateway:startup` | Verify Docker daemon, Redis, SQLite; load hook registry |
| Startup | `agent:bootstrap` | Inject workspace config, register dynamic MCP tools |
| Runtime | `message:received` | Content safety scan, audit log write |
| Runtime | `command:new` | Run `hook_validate` before execution |
| Runtime | `session:patch` | Update session metadata in audit trail |
| Compaction | `session:compact:before` | Save structured summary to external memory |
| Compaction | `session:compact:after` | Verify summary integrity, log compaction stats |
| Shutdown | `gateway:shutdown` | Flush Prometheus metrics, close DB connections |
| Restart | `gateway:pre-restart` | Drain in-flight sandbox executions |

## Available Templates

| Template | Trigger | Action |
|----------|---------|--------|
| `command_validate.yaml` | `command:new` | Run through `hook_validate` allow-list + sandbox |
| `session_compact_summary.yaml` | `session:compact:before` | Persist structured summary before context loss |
| `gateway_startup_health.yaml` | `gateway:startup` | Fail-fast subsystem health check |

## Synergy with Business Hooks

The agent runtime hooks govern the **AI's own behavior**.
The business event hooks govern the **AI's effect on the world**.
Together, they form the full trust boundary for an autonomous agent.

## The Composed Pattern

```
Agent Runtime hooks
  ├── command:new → hook_validate (security gate)
  └── message:received → audit log
          │
          ▼
    AI decides to act
          │
          ▼
Hook CLI MCP (business layer)
  ├── hook_validate dry-run
  ├── human approval
  └── sandbox execution → business system + audit
```

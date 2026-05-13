# Hook Templates

Ready-to-use hook configurations for common business automation patterns.
Each template maps directly to the `hook_create` MCP tool call or can be
loaded via `hookcli hook create --from-template <file>`.

## Available Templates

### Business Event Hooks

| Template | Trigger | Binaries | Use Case |
|----------|---------|----------|----------|
| `stripe_payment_recovery.yaml` | `payment_intent.payment_failed` | `stripe`, `curl` | Card errors trigger recovery portal |
| `github_build_retry.yaml` | `workflow_run.failed` | `gh`, `curl` | Failed builds retry; second failure creates Jira bug |

### Agent Runtime Hooks (v1.2.0)

These templates govern the **AI's own lifecycle** — startup, command execution, and session
compaction. They sit one layer above the business hooks and apply the same security model to
the agent runtime itself.

| Template | Trigger | Action |
|----------|---------|--------|
| `agent_runtime/command_validate.yaml` | `command:new` | Run through `hook_validate` allow-list + sandbox before execution |
| `agent_runtime/session_compact_summary.yaml` | `session:compact:before` | Persist structured summary before context loss |
| `agent_runtime/gateway_startup_health.yaml` | `gateway:startup` | Fail-fast subsystem health check; refuse degraded startup |

See [`agent_runtime/README.md`](agent_runtime/README.md) for the full event taxonomy
and the composed architecture (runtime hooks + business hooks = full trust boundary).

## Usage

### Via AI client (Claude Desktop / Cursor / Copilot)

```
hook_create(
  name="stripe_payment_recovery",
  source="webhook",
  filter_expr=".type == \"payment_intent.payment_failed\"",
  command="stripe ... && curl ...",
  approval_required=false
)
```

### Via `hook_validate` before deploying

Always dry-run a template before registering it:

```bash
curl -s -X POST http://localhost:8000/api/tools/validate \
  -H "Content-Type: application/json" \
  -d '{
    "command": "stripe billing_portal_configuration create --customer evt_test",
    "payload": {"data": {"object": {"customer": "cus_test", "id": "pi_test"}}},
    "secrets": {"STRIPE_API_KEY": "sk_test_mock"},
    "timeout_sec": 10
  }'
```

## Required CLI Binaries

Install on the Hook CLI MCP host or add to the sandbox image:

| Binary | Use Cases | Install |
|--------|-----------|---------|
| `stripe` | Payment recovery, fraud detection | `npm install -g @stripe/stripe-cli` |
| `gh` | CI/CD remediation, onboarding | `winget install GitHub.cli` |
| `aws` | Cloud scaling, DNS failover, compliance | `winget install Amazon.AWSCLI` |
| `jira` | Ticket creation, support triage | `npm install -g jira-cli` |
| `gcloud` | Multi-cloud cost, GCP operations | `winget install Google.CloudSDK` |
| `kubectl` | Container orchestration | `winget install Kubernetes.kubectl` |
| `psql` | Database queries, inventory | Included with PostgreSQL |

All binaries must also be in `ALLOWED_BINARIES` in `hookcli_mcp/core/validator.py`.

## Security Model

Every command in every template runs through:

1. **Template rendering** — `{{ event.field }}` and `{{ secret('KEY') }}` resolved safely
2. **Regex pre-filter** — blocks `rm -rf`, `sudo`, file overwrites
3. **Allow-list policy** — only binaries in `ALLOWED_BINARIES` can execute
4. **Dry-run sandbox** — `network_disabled=True`, read-only FS, `pids_limit=32`
5. **Human approval** — set `approval_required: true` for destructive commands
6. **Audit log** — every execution recorded in SQLite with actor, timestamp, exit code

## Adding New Templates

1. Copy an existing template as a starting point
2. Set `event_type` to match the incoming webhook event
3. Write `filter_expr` as a `jq` expression that selects the relevant events
4. Write `command` using `{{ event.* }}` and `{{ secret('KEY') }}` placeholders
5. Set `required_binaries` — ensure each is in `ALLOWED_BINARIES`
6. Set `approval_required: true` for any destructive operations
7. Run `hook_validate` with a sample payload before deploying

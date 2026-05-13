# Hook CLI MCP — TypeScript Companion

Lightweight Node.js MCP server for environments where Docker isn't available.
Shares the same tool contracts, JSON Schema, and `ALLOWED_BINARIES` policy
as the Python implementation — without the sandbox execution layer.

## Quick Start

```bash
cd typescript
npm install
npm run build
npm start
```

## MCP Client Setup

Add to your `mcp.json` (Claude Desktop / Cursor / Copilot):

```json
{
  "mcpServers": {
    "hookcli-mcp-ts": {
      "command": "node",
      "args": ["path/to/hookcli-mcp/typescript/dist/server.js"]
    }
  }
}
```

## Tools (matching Python contract)

| Tool | Description |
|------|-------------|
| `register_event_hook` | Register a webhook event listener |
| `hook_validate` | Dry-run a CLI command — allow-list + regex guards |
| `execute_remediation` | Trigger a corrective action for a captured event |
| `bottleneck_analyze` | Analyze failures and suggest remediation hooks |

## Python vs TypeScript

| Feature | Python (Hardened) | TypeScript (Lightweight) |
|---------|-------------------|--------------------------|
| Sandbox | Docker + seccomp | None — template validation only |
| State | SQLite + Redis | In-memory Map (swap for SQLite in production) |
| Observability | OTel + Jaeger + Prometheus | Console logs |
| Security | Allow-list + regex + HITL | Same allow-list + regex, no sandbox |
| Transport | stdio + SSE/HTTP | stdio |

Use the Python server for production workloads.
Use this server for quick prototyping and Node.js-native environments.

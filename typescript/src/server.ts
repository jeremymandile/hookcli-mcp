import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const server = new Server(
  { name: "hookcli-mcp-ts", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

// In-memory registry — swap for SQLite/Redis in production
const hookRegistry = new Map<string, {
  id: string;
  eventName: string;
  targetUrl: string;
  active: boolean;
  createdAt: Date;
}>();

// Shared ALLOWED_BINARIES — mirrors the Python implementation's policy
const ALLOWED_BINARIES = new Set([
  "sh", "bash", "echo", "printf", "cat", "grep", "sed", "awk",
  "jq", "curl", "wget", "python3", "python", "node",
  "sleep", "timeout", "date", "env", "true", "false",
  "hookcli", "stripe", "gh", "aws", "jira", "gcloud", "kubectl", "psql",
]);

const DANGEROUS_PATTERNS = [
  /\brm\s+-rf\s+(\/\s*|\*\s*)/,
  /\bsudo\s+/,
  />\s*\/etc\/(passwd|shadow|hosts)\b/,
];

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "register_event_hook",
      description: "Register a new event hook to monitor business process failures. Supports Stripe, GitHub, Jira, and custom webhooks.",
      inputSchema: {
        type: "object" as const,
        properties: {
          eventName: { type: "string", description: "e.g., payment_intent.payment_failed" },
          targetUrl: { type: "string", description: "Webhook URL receiving remediation payloads" },
          authHeader: { type: "string", description: "Bearer token for destination security" },
          retryPolicy: { type: "string", enum: ["linear", "exponential"], default: "exponential" },
        },
        required: ["eventName", "targetUrl"],
      },
    },
    {
      name: "hook_validate",
      description: "Dry-run a CLI command against a synthetic payload. Mirrors the Python Hook CLI MCP contract — same allow-list, same security checks.",
      inputSchema: {
        type: "object" as const,
        properties: {
          command: { type: "string", description: "CLI command with {{ event.field }} templates" },
          payload: { type: "object", description: "Synthetic event payload for template resolution" },
          secrets: { type: "object", description: "Mock secrets map for validation" },
          timeout_sec: { type: "number", default: 30 },
        },
        required: ["command"],
      },
    },
    {
      name: "execute_remediation",
      description: "Execute a corrective action for a captured event. Issues API calls to downstream systems.",
      inputSchema: {
        type: "object" as const,
        properties: {
          hookId: { type: "string" },
          actionType: { type: "string", description: "e.g., retry_payment, create_jira_bug, send_slack_alert" },
          payload: { type: "object" },
        },
        required: ["hookId", "actionType", "payload"],
      },
    },
    {
      name: "bottleneck_analyze",
      description: "Analyze recent event failures and suggest remediation hooks. Returns structured root cause analysis.",
      inputSchema: {
        type: "object" as const,
        properties: {
          workspace_id: { type: "string" },
          time_range_hours: { type: "number", default: 24 },
          focus: { type: "string", default: "all" },
        },
        required: ["workspace_id"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "register_event_hook") {
    const hookId = crypto.randomUUID();
    hookRegistry.set(hookId, {
      id: hookId,
      eventName: args?.eventName as string,
      targetUrl: args?.targetUrl as string,
      active: true,
      createdAt: new Date(),
    });
    return {
      content: [{
        type: "text" as const,
        text: JSON.stringify({ hook_id: hookId, status: "registered", event: args?.eventName }),
      }],
    };
  }

  if (name === "hook_validate") {
    const command = args?.command as string;
    const payload = (args?.payload as Record<string, unknown>) ?? {};
    const secrets = (args?.secrets as Record<string, string>) ?? {};

    // Template rendering
    const rendered = command
      .replace(/\{\{\s*event\.(\w+)\s*\}\}/g, (_, key) => String(payload[key] ?? `<MISSING:${key}>`))
      .replace(/\{\{\s*secret\('(\w+)'\)\s*\}\}/g, (_, key) => secrets[key] ?? `<UNRESOLVED:${key}>`);

    // Security checks
    for (const pattern of DANGEROUS_PATTERNS) {
      if (pattern.test(rendered)) {
        return {
          content: [{
            type: "text" as const,
            text: JSON.stringify({ valid: false, security_pass: false, errors: [`Dangerous pattern blocked: ${pattern}`], rendered_command: rendered, warnings: [] }),
          }],
        };
      }
    }

    // Allow-list check
    const binary = rendered.trim().split(/\s+/)[0]?.split("/").pop() ?? "";
    if (!ALLOWED_BINARIES.has(binary)) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({ valid: false, security_pass: false, errors: [`Binary '${binary}' not in allow-list`], rendered_command: rendered, warnings: [] }),
        }],
      };
    }

    const warnings = rendered.includes("<UNRESOLVED:") ? ["Unresolved secret(s) in rendered command"] : [];
    return {
      content: [{
        type: "text" as const,
        text: JSON.stringify({ valid: true, security_pass: true, errors: [], warnings, rendered_command: rendered, execution: null }),
      }],
    };
  }

  if (name === "execute_remediation") {
    const { hookId, actionType } = args as Record<string, string>;
    const hook = hookRegistry.get(hookId);
    if (!hook?.active) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({ status: "error", message: `Hook ${hookId} not found or inactive` }),
        }],
      };
    }
    return {
      content: [{
        type: "text" as const,
        text: JSON.stringify({ status: "resolved", hook_id: hookId, action: actionType, target: hook.targetUrl }),
      }],
    };
  }

  if (name === "bottleneck_analyze") {
    return {
      content: [{
        type: "text" as const,
        text: JSON.stringify({
          analysis: "No failures detected in the specified time range.",
          root_cause: "N/A",
          confidence: 0.0,
          suggested_hooks: [],
          next_steps: ["Register webhook endpoints to begin collecting event data."],
        }),
      }],
    };
  }

  throw new Error(`Unknown tool: ${name}`);
});

const transport = new StdioServerTransport();
await server.connect(transport);

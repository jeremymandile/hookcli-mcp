# Re-export from canonical location to avoid duplicate Prometheus registration.
from hookcli_mcp.observability.metrics import record_hook_execution  # noqa: F401

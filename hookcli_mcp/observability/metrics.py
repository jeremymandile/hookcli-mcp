from prometheus_client import Counter, Histogram

HOOK_EXECUTIONS = Counter(
    "hook_execution_total", "Total hook executions", ["hook_id", "status"]
)
HOOK_EXECUTION_LATENCY = Histogram(
    "hook_execution_duration_seconds",
    "Hook execution latency in seconds",
    ["hook_id"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)
HOOK_RETRIES = Counter("hook_retry_total", "Number of retries per hook", ["hook_id"])
DLQ_EVENTS = Counter("hook_dlq_total", "Events sent to dead letter queue", ["hook_id"])


def record_execution(hook_id: str, duration: float, success: bool):
    status = "success" if success else "failure"
    HOOK_EXECUTIONS.labels(hook_id=hook_id, status=status).inc()
    HOOK_EXECUTION_LATENCY.labels(hook_id=hook_id).observe(duration)


def record_retry(hook_id: str):
    HOOK_RETRIES.labels(hook_id=hook_id).inc()


def record_dlq(hook_id: str):
    DLQ_EVENTS.labels(hook_id=hook_id).inc()

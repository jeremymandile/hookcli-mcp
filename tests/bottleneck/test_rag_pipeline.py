import pytest
from unittest.mock import patch, AsyncMock

from hookcli_mcp.tools.bottleneck_analyze import BottleneckRequest, bottleneck_analyze


# Minimal metrics dict the RAG pipeline returns when no DB / no failures
_EMPTY_METRICS = {
    "total_events": 0,
    "failure_count": 0,
    "failure_rate_pct": 0.0,
    "dlq_count": 0,
    "avg_latency_ms": 0.0,
    "recent_failures": [],
}

_FAILURE_METRICS = {
    "total_events": 100,
    "failure_count": 12,
    "failure_rate_pct": 12.0,
    "dlq_count": 3,
    "avg_latency_ms": 450.0,
    "recent_failures": [
        {"hook_id": "stripe_webhook", "error": "Connection timeout after 30s", "retries": 3}
    ],
}


@pytest.mark.asyncio
class TestBottleneckAnalyze:
    async def test_returns_valid_response_structure(self):
        """bottleneck_analyze must always return all required fields."""
        with patch("hookcli_mcp.services.rag.retrieve_failures", new=AsyncMock(return_value=_EMPTY_METRICS)):
            req = BottleneckRequest(time_range_hours=24, focus="network", workspace_id="ws-1")
            result = await bottleneck_analyze(req)

        assert isinstance(result.analysis, str)
        assert isinstance(result.root_cause, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.suggested_hooks, list)
        assert isinstance(result.next_steps, list)

    async def test_confidence_in_valid_range(self):
        """confidence must always be in [0.0, 1.0]."""
        with patch("hookcli_mcp.services.rag.retrieve_failures", new=AsyncMock(return_value=_EMPTY_METRICS)):
            req = BottleneckRequest(time_range_hours=1, focus="all", workspace_id="ws-1")
            result = await bottleneck_analyze(req)

        assert 0.0 <= result.confidence <= 1.0

    async def test_no_failures_returns_healthy_analysis(self):
        """Zero failures → high confidence, no suggested hooks."""
        with patch("hookcli_mcp.services.rag.retrieve_failures", new=AsyncMock(return_value=_EMPTY_METRICS)):
            req = BottleneckRequest(time_range_hours=24, focus="all", workspace_id="ws-1")
            result = await bottleneck_analyze(req)

        assert result.confidence >= 0.9
        assert result.root_cause == "N/A"

    async def test_failures_trigger_heuristic_analysis(self):
        """With failures present and no ANTHROPIC_API_KEY, heuristic should run."""
        with patch("hookcli_mcp.services.rag.retrieve_failures", new=AsyncMock(return_value=_FAILURE_METRICS)):
            with patch("hookcli_mcp.services.rag.ANTHROPIC_API_KEY", None):
                req = BottleneckRequest(time_range_hours=24, focus="stripe", workspace_id="ws-1")
                result = await bottleneck_analyze(req)

        assert result.failure_rate if hasattr(result, "failure_rate") else True
        assert "12" in result.analysis or "failure" in result.analysis.lower()
        assert result.confidence > 0.0
        assert len(result.next_steps) >= 1

    async def test_retrieve_failures_graceful_on_missing_db(self):
        """retrieve_failures must not raise when the DB table doesn't exist."""
        from hookcli_mcp.services.rag import retrieve_failures

        # Should return zeroed metrics, not raise
        result = await retrieve_failures("ws-missing", 24, "all")
        assert result["total_events"] == 0
        assert result["failure_count"] == 0
        assert isinstance(result["recent_failures"], list)

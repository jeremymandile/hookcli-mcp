import pytest

from hookcli_mcp.tools.bottleneck_analyze import BottleneckRequest, bottleneck_analyze


@pytest.mark.asyncio
class TestBottleneckAnalyze:
    async def test_returns_valid_response(self):
        req = BottleneckRequest(time_range_hours=24, focus="network", workspace_id="ws-1")
        result = await bottleneck_analyze(req)
        assert isinstance(result.analysis, str)
        assert isinstance(result.root_cause, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.suggested_hooks, list)
        assert isinstance(result.next_steps, list)

    async def test_confidence_in_range(self):
        req = BottleneckRequest(time_range_hours=1, focus="all", workspace_id="ws-1")
        result = await bottleneck_analyze(req)
        assert 0.0 <= result.confidence <= 1.0

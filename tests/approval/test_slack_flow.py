from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hookcli_mcp.services.approval import request_approval


@pytest.mark.asyncio
class TestApprovalFlow:
    @patch("hookcli_mcp.services.approval.SLACK_BOT_TOKEN", "xoxb-fake-token")
    @patch("hookcli_mcp.services.approval.httpx.AsyncClient")
    async def test_approval_posts_to_slack(self, mock_client):
        mock_post = AsyncMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await request_approval("h-1", "e-1", {}, "echo test", "#test")
        assert result is True
        mock_post.assert_called_once()

    async def test_approval_returns_false_without_token(self):
        import os

        original = os.environ.pop("SLACK_BOT_TOKEN", None)
        try:
            import hookcli_mcp.services.approval as svc

            svc.SLACK_BOT_TOKEN = None
            result = await request_approval("h-1", "e-1", {}, "echo test")
            assert result is False
        finally:
            if original:
                os.environ["SLACK_BOT_TOKEN"] = original

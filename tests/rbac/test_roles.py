import pytest
from fastapi import HTTPException

from hookcli_mcp.auth.rbac import _allowed_roles, require_role


@pytest.mark.asyncio
class TestRBAC:
    async def test_viewer_blocked_from_operator_action(self):
        ctx = {"workspace_id": "ws-1", "role": "viewer"}

        async def mock_create(**kwargs):
            return {"status": "created"}

        wrapped = require_role("operator")(mock_create)
        with pytest.raises(HTTPException) as exc_info:
            await wrapped(context=ctx)
        assert exc_info.value.status_code == 403

    async def test_admin_passes_operator_check(self):
        ctx = {"workspace_id": "ws-1", "role": "admin"}

        async def mock_create(**kwargs):
            return {"status": "created"}

        wrapped = require_role("operator")(mock_create)
        result = await wrapped(context=ctx)
        assert result["status"] == "created"

    async def test_admin_passes_admin_check(self):
        ctx = {"workspace_id": "ws-1", "role": "admin"}

        async def mock_delete(**kwargs):
            return {"status": "deleted"}

        wrapped = require_role("admin")(mock_delete)
        result = await wrapped(context=ctx)
        assert result["status"] == "deleted"

    async def test_operator_blocked_from_admin_action(self):
        ctx = {"workspace_id": "ws-1", "role": "operator"}

        async def mock_delete(**kwargs):
            return {"status": "deleted"}

        wrapped = require_role("admin")(mock_delete)
        with pytest.raises(HTTPException) as exc_info:
            await wrapped(context=ctx)
        assert exc_info.value.status_code == 403

    def test_allowed_roles_hierarchy(self):
        assert "admin" in _allowed_roles("viewer")
        assert "operator" in _allowed_roles("viewer")
        assert "viewer" in _allowed_roles("viewer")
        assert "admin" in _allowed_roles("operator")
        assert "viewer" not in _allowed_roles("operator")
        assert "admin" in _allowed_roles("admin")
        assert "operator" not in _allowed_roles("admin")

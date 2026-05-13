"""
Integration tests for the MCP stdio transport.

Spawns hookcli_mcp.server as a real subprocess, connects via the MCP client
protocol over stdio, and verifies tool registration and invocation end-to-end —
the same path Claude Desktop / Cursor / any MCP client uses.

Run with:
    pytest tests/test_mcp_transport.py -v

Each test manages its own session (no shared fixture) to avoid anyio cancel-scope
issues when the fixture is torn down across task boundaries in pytest-asyncio.
"""

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PYTHON = sys.executable
PROJECT_ROOT = Path(__file__).parent.parent


@asynccontextmanager
async def mcp_session():
    """Spawn the stdio server and yield an initialised MCP ClientSession."""
    params = StdioServerParameters(
        command=PYTHON,
        args=["-m", "hookcli_mcp.server_stdio"],
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@pytest.mark.asyncio
async def test_tool_list_contains_expected_tools():
    """Server must advertise hook_validate and bottleneck_analyze."""
    async with mcp_session() as session:
        response = await session.list_tools()
        tool_names = {t.name for t in response.tools}
        assert "hook_validate" in tool_names, f"hook_validate missing from {tool_names}"
        assert "bottleneck_analyze" in tool_names, f"bottleneck_analyze missing from {tool_names}"


@pytest.mark.asyncio
async def test_tool_descriptions_present():
    """Every registered tool must have a non-empty description."""
    async with mcp_session() as session:
        response = await session.list_tools()
        for tool in response.tools:
            assert tool.description, f"tool '{tool.name}' has no description"


@pytest.mark.asyncio
async def test_hook_validate_safe_command():
    """A simple echo command should pass validation and execute successfully."""
    async with mcp_session() as session:
        result = await session.call_tool("hook_validate", {
            "command": "echo hello from mcp",
            "payload": {},
            "secrets": {},
            "timeout_sec": 15,
        })
        data = json.loads(result.content[0].text)

        assert data["valid"] is True, f"Expected valid=True, got errors: {data['errors']}"
        assert data["security_pass"] is True
        assert data["rendered_command"] == "echo hello from mcp"
        assert data["execution"]["exit_code"] == 0
        assert "hello from mcp" in data["execution"]["stdout"]


@pytest.mark.asyncio
async def test_hook_validate_template_rendering():
    """Event fields must be interpolated into the rendered command."""
    async with mcp_session() as session:
        result = await session.call_tool("hook_validate", {
            "command": "echo order={{ event.order_id }} amount={{ event.amount }}",
            "payload": {"order_id": "ord_42", "amount": 9900},
            "timeout_sec": 15,
        })
        data = json.loads(result.content[0].text)

        assert data["valid"] is True
        assert "ord_42" in data["rendered_command"]
        assert "9900" in data["rendered_command"]


@pytest.mark.asyncio
async def test_hook_validate_blocks_dangerous_command():
    """rm -rf / must be rejected by the security guard before reaching the sandbox."""
    async with mcp_session() as session:
        result = await session.call_tool("hook_validate", {
            "command": "rm -rf /",
            "payload": {},
            "timeout_sec": 10,
        })
        data = json.loads(result.content[0].text)

        assert data["valid"] is False
        assert data["security_pass"] is False
        assert any("Recursive root deletion" in e for e in data["errors"])


@pytest.mark.asyncio
async def test_hook_validate_blocks_unlisted_binary():
    """Binaries not in ALLOWED_BINARIES must be rejected by the allow-list policy."""
    async with mcp_session() as session:
        result = await session.call_tool("hook_validate", {
            "command": "nmap -sV 10.0.0.1",
            "payload": {},
            "timeout_sec": 10,
        })
        data = json.loads(result.content[0].text)

        assert data["valid"] is False
        assert any("allow-list" in e for e in data["errors"])


@pytest.mark.asyncio
async def test_hook_validate_warns_unresolved_secret():
    """Commands referencing secrets not in secrets_map must trigger a warning."""
    async with mcp_session() as session:
        result = await session.call_tool("hook_validate", {
            "command": 'curl https://api.example.com -H "Auth: {{ secret(\'MISSING_KEY\') }}"',
            "payload": {},
            "secrets": {},
            "timeout_sec": 15,
        })
        data = json.loads(result.content[0].text)

        assert any("UNRESOLVED" in w for w in data["warnings"]), (
            f"Expected UNRESOLVED warning, got: {data['warnings']}"
        )


@pytest.mark.asyncio
async def test_bottleneck_analyze_returns_valid_structure():
    """bottleneck_analyze must return all required fields with correct types."""
    async with mcp_session() as session:
        result = await session.call_tool("bottleneck_analyze", {
            "workspace_id": "test-workspace",
            "time_range_hours": 1,
            "focus": "payment",
        })
        data = json.loads(result.content[0].text)

        assert "analysis" in data
        assert "root_cause" in data
        assert "confidence" in data
        assert isinstance(data["suggested_hooks"], list)
        assert isinstance(data["next_steps"], list)
        assert 0.0 <= data["confidence"] <= 1.0

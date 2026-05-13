"""Subprocess entry point for the MCP stdio transport.

Invoked by `python -m hookcli_mcp.server_stdio` during integration tests
and by `hookcli-mcp-stdio` CLI entry point. Runs ONLY the stdio loop —
no uvicorn, no HTTP, no stdout noise that would corrupt the MCP framing.
"""

from hookcli_mcp.server import stdio_main

if __name__ == "__main__":
    stdio_main()

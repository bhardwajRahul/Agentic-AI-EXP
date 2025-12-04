"""
Shared MCP server instance for all Google service tools.
"""

from mcp.server.fastmcp import FastMCP

server = FastMCP(
    name="Google Services Assistant",
    host="0.0.0.0",
    port=8050,
    stateless_http=True,
)

__all__ = ["server"]

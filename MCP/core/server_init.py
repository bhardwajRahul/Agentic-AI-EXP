from mcp.server.fastmcp import FastMCP

# Communication Server
comm_server = FastMCP(
    name="Communication Server",
    host="0.0.0.0",
    port=8050,
    stateless_http=True,
)

# Productivity Server
prod_server = FastMCP(
    name="Productivity Server",
    host="0.0.0.0",
    port=8051,
    stateless_http=True,
)

content_server = FastMCP(
    name="Content Server",
    host="0.0.0.0",
    port=8052,
    stateless_http=True,
)

__all__ = ["comm_server", "prod_server", "content_server"]

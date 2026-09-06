from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from mcp.server.mcpserver import MCPServer


def build_mcp_server(
    name: str,
    version: str,
    instructions: str | None = None,
    lifespan: Callable[[MCPServer], AbstractAsyncContextManager[Any]] | None = None,
) -> MCPServer:

    server = MCPServer(
        name=name,
        version=version,
        instructions=instructions,
        lifespan=lifespan,
    )

    return server

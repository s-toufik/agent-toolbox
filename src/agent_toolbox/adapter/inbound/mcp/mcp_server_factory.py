from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from mcp.server._otel import OpenTelemetryMiddleware
from mcp.server.mcpserver import MCPServer

from agent_toolbox.adapter.inbound.mcp.request_spans import RequestSpans


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
    server.middleware[:] = [
        RequestSpans(middleware) if isinstance(middleware, OpenTelemetryMiddleware) else middleware
        for middleware in server.middleware
    ]

    return server

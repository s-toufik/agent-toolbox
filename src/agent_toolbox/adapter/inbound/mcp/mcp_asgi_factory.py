import os
from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from urllib.parse import urlparse

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pycraftcore.application_configuration.model.connector import McpConnector
from pycraftcore.web.middleware import RequestIDMiddleware
from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware

from agent_toolbox.domain.model.tool_scope import ToolScope

DEFAULT_PATH: str = "/mcp"


def scope_path(base_path: str, scope: ToolScope) -> str:
    return base_path if scope.is_all else f"{base_path}/{scope.name}"


def mcp_base_path(connector: McpConnector) -> str:
    return urlparse(connector.base_url).path.rstrip("/") or DEFAULT_PATH


def build_mcp_asgi_app(
    servers: Mapping[ToolScope, MCPServer], connector: McpConnector
) -> Starlette:
    url = urlparse(connector.base_url)
    allowed_hosts = [url.netloc] if url.netloc else []
    allowed_hosts += _extra_allowed_hosts()
    security = TransportSecuritySettings(allowed_hosts=allowed_hosts)
    base_path: str = mcp_base_path(connector)

    children: list[Starlette] = [
        server.streamable_http_app(
            streamable_http_path=scope_path(base_path, scope),
            json_response=True,
            stateless_http=True,
            transport_security=security,
        )
        for scope, server in servers.items()
    ]
    app = Starlette(
        routes=[route for child in children for route in child.routes],
        lifespan=_running(children),
    )

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(RequestIDMiddleware)

    return app


def _running(
    children: list[Starlette],
) -> Callable[[Starlette], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncGenerator[None]:
        async with AsyncExitStack() as stack:
            for child in children:
                await stack.enter_async_context(child.router.lifespan_context(child))
            yield

    return lifespan


def _extra_allowed_hosts() -> list[str]:
    raw = os.getenv("TOOLBOX_EXTRA_ALLOWED_HOSTS", "")
    return [host.strip() for host in raw.split(",") if host.strip()]

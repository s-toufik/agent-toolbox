from urllib.parse import urlparse

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pycraftcore.application_configuration.model.connector import McpConnector
from pycraftcore.http.middleware import RequestIDMiddleware
from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware


def build_mcp_asgi_app(server: MCPServer, connector: McpConnector) -> Starlette:

    url = urlparse(connector.base_url)
    path = url.path or "/mcp"

    app: Starlette = server.streamable_http_app(
        streamable_http_path=path,
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[url.netloc] if url.netloc else [],
        ),
    )

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(RequestIDMiddleware)

    return app

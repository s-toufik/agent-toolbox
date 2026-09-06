from urllib.parse import urlparse

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pycraftcore.application_configuration.model.connector import McpConnector
from starlette.applications import Starlette


def build_mcp_asgi_app(server: MCPServer, connector: McpConnector) -> Starlette:

    url = urlparse(connector.base_url)
    path = url.path or "/mcp"

    return server.streamable_http_app(
        streamable_http_path=path,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[url.netloc] if url.netloc else [],
        ),
    )

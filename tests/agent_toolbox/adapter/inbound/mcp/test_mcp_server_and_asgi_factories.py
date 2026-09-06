from pycraftcore.application_configuration.enum import ConnectorType
from pycraftcore.application_configuration.model.connector import McpConnector
from pycraftcore.authentication.model.no_auth import NoAuth
from starlette.testclient import TestClient

from agent_toolbox.adapter.inbound.mcp.mcp_asgi_factory import build_mcp_asgi_app
from agent_toolbox.adapter.inbound.mcp.mcp_server_factory import build_mcp_server


def make_connector(base_url: str = "http://localhost:8001/mcp") -> McpConnector:
    return McpConnector(
        name="self",
        type=ConnectorType.mcp,
        auth=NoAuth(),
        base_url=base_url,
        timeout=30,
        transport="streamable_http",
    )


def test_the_mcp_endpoint_is_served_at_the_path_from_the_connector_url() -> None:
    server = build_mcp_server(name="toolbox", version="1.0.0")
    app = build_mcp_asgi_app(server, make_connector("http://localhost:8001/custom-path"))

    with TestClient(app, base_url="http://localhost:8001") as client:
        response = client.post(
            "/custom-path",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "t", "version": "0"},
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

    assert response.status_code == 200


def test_defaults_to_slash_mcp_when_the_connector_url_has_no_path() -> None:
    server = build_mcp_server(name="toolbox", version="1.0.0")
    app = build_mcp_asgi_app(server, make_connector("http://localhost:8001"))

    with TestClient(app, base_url="http://localhost:8001") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "t", "version": "0"},
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )

    assert response.status_code == 200

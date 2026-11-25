from pycraftcore.application_configuration.enum import ConnectorType
from pycraftcore.application_configuration.model import McpConnector
from pycraftcore.authentication.model.no_auth import NoAuth
from starlette.testclient import TestClient

from agent_toolbox.adapter.inbound.mcp.mcp_asgi_factory import build_mcp_asgi_app
from agent_toolbox.adapter.inbound.mcp.mcp_server_factory import build_mcp_server
from agent_toolbox.domain.model.tool_scope import ALL_TOOLS, ToolScope


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
    app = build_mcp_asgi_app(
        {ALL_TOOLS: server}, make_connector("http://localhost:8001/custom-path")
    )

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
    app = build_mcp_asgi_app({ALL_TOOLS: server}, make_connector("http://localhost:8001"))

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


def _initialize_request(host: str) -> dict:
    return {
        "json": {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "0"},
            },
        },
        "headers": {"Accept": "application/json, text/event-stream", "Host": host},
    }


def test_a_host_from_toolbox_extra_allowed_hosts_is_accepted(monkeypatch) -> None:
    monkeypatch.setenv("TOOLBOX_EXTRA_ALLOWED_HOSTS", "sirius:8001, other-host:9000")

    server = build_mcp_server(name="toolbox", version="1.0.0")
    app = build_mcp_asgi_app({ALL_TOOLS: server}, make_connector("http://localhost:8001/mcp"))

    with TestClient(app, base_url="http://localhost:8001") as client:
        response = client.post("/mcp", **_initialize_request("sirius:8001"))

    assert response.status_code == 200


def test_a_host_not_in_the_allowed_list_is_still_rejected(monkeypatch) -> None:
    monkeypatch.delenv("TOOLBOX_EXTRA_ALLOWED_HOSTS", raising=False)

    server = build_mcp_server(name="toolbox", version="1.0.0")
    app = build_mcp_asgi_app({ALL_TOOLS: server}, make_connector("http://localhost:8001/mcp"))

    with TestClient(app, base_url="http://localhost:8001") as client:
        response = client.post("/mcp", **_initialize_request("not-allowed:8001"))

    assert response.status_code == 421


def _initialize(client: TestClient, path: str):
    return client.post(
        path,
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


def test_each_scope_is_served_under_the_base_path_with_its_own_server() -> None:
    servers = {
        ALL_TOOLS: build_mcp_server(name="toolbox", version="1.0.0"),
        ToolScope("observation", ("grafana_*",)): build_mcp_server(
            name="toolbox-observation", version="1.0.0"
        ),
    }
    app = build_mcp_asgi_app(servers, make_connector("http://localhost:8001/mcp"))

    with TestClient(app, base_url="http://localhost:8001") as client:
        everything = _initialize(client, "/mcp").json()
        observation = _initialize(client, "/mcp/observation").json()
        unknown = _initialize(client, "/mcp/kitchen")

    assert everything["result"]["serverInfo"]["name"] == "toolbox"
    assert observation["result"]["serverInfo"]["name"] == "toolbox-observation"
    assert unknown.status_code == 404

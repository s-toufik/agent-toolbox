import pytest
from starlette.testclient import TestClient

from bootstrap.application.toolbox_application import create_toolbox_application

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "t", "version": "0"},
    },
}
TOOLS_LIST = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
ACCEPT = {"Accept": "application/json, text/event-stream"}


@pytest.fixture
def client(make_settings):
    with TestClient(
        create_toolbox_application(make_settings(extra_allowed_hosts=("sirius:8001",))),
        base_url="http://127.0.0.1:8001",
    ) as client:
        yield client


def bearer(client: TestClient, username: str = "toufik", expire: str | None = "never") -> dict:
    body = {"username": username} | ({"expire": expire} if expire else {})
    token = client.post("/auth/token", json=body).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def tools(client: TestClient, path: str, headers: dict) -> set[str]:
    answer = client.post(path, json=TOOLS_LIST, headers=ACCEPT | headers).json()
    return {tool["name"] for tool in answer["result"]["tools"]}


def test_the_actuator_is_open_and_reports_ready_once_booted(client) -> None:
    readiness = client.get("/actuator/health/readiness")
    info = client.get("/actuator/info").json()

    assert (readiness.status_code, readiness.json()) == (200, {"status": "UP"})
    assert info["name"] == "agent-toolbox"


def test_each_scope_is_served_at_its_path_with_its_own_server_name(client) -> None:
    auth = bearer(client)

    everything = client.post("/mcp", json=INITIALIZE, headers=ACCEPT | auth).json()
    kitchen = client.post("/mcp/kitchen", json=INITIALIZE, headers=ACCEPT | auth).json()

    assert everything["result"]["serverInfo"]["name"] == "toolbox"
    assert kitchen["result"]["serverInfo"]["name"] == "toolbox-kitchen"
    assert tools(client, "/mcp", auth) == {
        "users_tables",
        "python_executor",
        "file_reader",
        "file_writer",
    }
    assert tools(client, "/mcp/coding", auth) == {"python_executor", "file_reader", "file_writer"}


def test_the_mcp_endpoints_ask_for_a_valid_bearer_token(client) -> None:
    anonymous = client.post("/mcp/kitchen", json=INITIALIZE, headers=ACCEPT)
    forged = client.post(
        "/mcp", json=INITIALIZE, headers=ACCEPT | {"Authorization": "Bearer not.a.token"}
    )

    assert (anonymous.status_code, anonymous.json()) == (
        401,
        {"detail": "a bearer token is required"},
    )
    assert forged.status_code == 401
    assert forged.headers["www-authenticate"] == 'Bearer error="invalid_token"'


def test_a_tool_call_through_mcp_runs_the_tool(client) -> None:
    call = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "python_executor", "arguments": {"code": "result = 6 * 7"}},
    }

    answer = client.post("/mcp/travel", json=call, headers=ACCEPT | bearer(client)).json()

    assert answer["result"]["structuredContent"]["result"] == 42


def test_only_the_configured_and_extra_hosts_are_accepted(client) -> None:
    auth = ACCEPT | bearer(client)

    allowed = client.post("/mcp", json=INITIALIZE, headers=auth | {"Host": "sirius:8001"})
    refused = client.post("/mcp", json=INITIALIZE, headers=auth | {"Host": "elsewhere:8001"})

    assert (allowed.status_code, refused.status_code) == (200, 421)

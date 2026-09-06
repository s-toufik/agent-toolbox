from starlette.testclient import TestClient

from agent_toolbox.adapter.inbound.mcp.actuator import ActuatorRouter
from agent_toolbox.adapter.inbound.mcp.mcp_server_factory import build_mcp_server


def make_client(*, with_tool: bool = False) -> TestClient:
    server = build_mcp_server(name="toolbox", version="1.0.0")

    if with_tool:

        @server.tool(name="echo", description="Echoes.")
        async def echo(text: str) -> str:
            return text

    ActuatorRouter(
        server=server,
        app_name="toolbox",
        app_version="1.0.0",
        app_deployment_environment="debug",
        app_api_root_path="/agentic",
        app_authors="dev@example.com",
    ).register_actuator_routes()

    return TestClient(server.streamable_http_app())


def test_health_is_always_up() -> None:
    client = make_client()

    response = client.get("/agentic/actuator/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_liveness_is_always_up() -> None:
    client = make_client()

    response = client.get("/agentic/actuator/health/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_readiness_is_down_with_no_tools_registered() -> None:
    client = make_client()

    response = client.get("/agentic/actuator/health/readiness")

    assert response.status_code == 503
    assert response.json() == {"status": "DOWN"}


def test_readiness_is_up_once_a_tool_is_registered() -> None:
    client = make_client(with_tool=True)

    response = client.get("/agentic/actuator/health/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_info_reports_the_constructor_fields() -> None:
    client = make_client()

    response = client.get("/agentic/actuator/info")

    assert response.json() == {
        "name": "toolbox",
        "version": "1.0.0",
        "environment": "debug",
        "api_root_path": "/agentic",
        "authors": "dev@example.com",
    }

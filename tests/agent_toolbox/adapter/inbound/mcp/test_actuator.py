from datetime import UTC, datetime

from starlette.testclient import TestClient

from agent_toolbox.adapter.inbound.mcp.actuator import ActuatorRouter
from agent_toolbox.adapter.inbound.mcp.mcp_server_factory import build_mcp_server
from agent_toolbox.domain.model.dependency_state import DependencyState


def make_client(*, with_tool: bool = False, dependencies=dict) -> TestClient:
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
        app_authors="dev@example.com",
        dependencies=dependencies,
    ).register_actuator_routes()

    return TestClient(server.streamable_http_app())


def test_health_is_always_up() -> None:
    client = make_client()

    response = client.get(f"{ActuatorRouter.PREFIX}/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_liveness_is_always_up() -> None:
    client = make_client()

    response = client.get(f"{ActuatorRouter.PREFIX}/health/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_readiness_is_down_with_no_tools_registered() -> None:
    client = make_client()

    response = client.get(f"{ActuatorRouter.PREFIX}/health/readiness")

    assert response.status_code == 503
    assert response.json() == {"status": "DOWN"}


def test_readiness_is_up_once_a_tool_is_registered() -> None:
    client = make_client(with_tool=True)

    response = client.get(f"{ActuatorRouter.PREFIX}/health/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_info_reports_the_constructor_fields() -> None:
    client = make_client()

    response = client.get(f"{ActuatorRouter.PREFIX}/info")

    assert response.json() == {
        "name": "toolbox",
        "version": "1.0.0",
        "environment": "debug",
        "authors": "dev@example.com",
    }


def test_health_lists_each_dependency_and_stays_up_when_one_is_down() -> None:
    since = datetime(2026, 11, 12, 10, 42, 7, tzinfo=UTC)
    client = make_client(
        dependencies=lambda: {
            "grafana": DependencyState(up=True, since=since),
            "mongodb": DependencyState(up=False, since=since, error="ConnectError: refused"),
        }
    )

    response = client.get(f"{ActuatorRouter.PREFIX}/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "UP",
        "dependencies": {
            "grafana": {"status": "UP", "since": "2026-11-12T10:42:07+00:00"},
            "mongodb": {
                "status": "DOWN",
                "since": "2026-11-12T10:42:07+00:00",
                "error": "ConnectError: refused",
            },
        },
    }

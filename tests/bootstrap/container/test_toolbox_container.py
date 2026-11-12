from pathlib import Path

import pytest
from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette
from starlette.testclient import TestClient

from agent_toolbox.adapter.inbound.mcp.actuator import ActuatorRouter
from agent_toolbox.application.port.outbound.tool_provider_port import ExternalSource
from bootstrap.configuration.settings import ProcessSettings
from bootstrap.container.toolbox_container import ToolboxContainer
from tests.agent_toolbox.stubs import Named

REAL_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


@pytest.fixture(autouse=True)
def _base_env(monkeypatch, tmp_path):
    monkeypatch.setenv("USER_DB_HOST", str(tmp_path))
    monkeypatch.setenv("USER_DB_NAME", "users")
    monkeypatch.setenv("CHECKPOINT_DB_HOST", str(tmp_path))
    monkeypatch.setenv("CHECKPOINT_DB_NAME", "checkpoint")
    monkeypatch.setenv("TOOLBOX_URL", "http://127.0.0.1:8001/mcp")


def make_settings() -> ProcessSettings:
    return ProcessSettings(
        role="toolbox",
        environment="debug",
        configuration_directory=REAL_CONFIG_DIR,
    )


def test_logging_and_application_configuration_expose_the_di_internals() -> None:
    container = ToolboxContainer(make_settings())

    assert container.logging is container._logging
    assert container.application_configuration is container._configuration


def test_mcp_server_is_built_once_and_cached() -> None:
    container = ToolboxContainer(make_settings())

    assert isinstance(container.mcp_server, MCPServer)
    assert container.mcp_server is container.mcp_server


def test_asgi_app_is_a_starlette_application() -> None:
    container = ToolboxContainer(make_settings())

    assert isinstance(container.asgi_app, Starlette)


async def test_boot_can_be_called_directly_without_the_asgi_lifespan() -> None:
    container = ToolboxContainer(make_settings())

    await container.boot()  # must not raise; registers real tools on container.mcp_server

    assert await container.mcp_server.list_tools()
    await container.stop()


class FlakyServer:
    def __init__(self) -> None:
        self.up = False

    async def tools(self):
        if not self.up:
            raise ConnectionError("refused")
        return [Named("grafana_search")]


async def test_an_mcp_server_that_starts_after_the_toolbox_joins_it_without_a_restart() -> None:
    container = ToolboxContainer(make_settings())
    grafana = FlakyServer()
    container.__dict__["_external_sources"] = [ExternalSource("grafana", grafana)]
    await container.boot()
    before = {tool.name for tool in await container.mcp_server.list_tools()}

    grafana.up = True
    await container._external_tools_reconciler.reconcile()

    after = {tool.name for tool in await container.mcp_server.list_tools()}
    assert "grafana_search" not in before
    assert "grafana_search" in after
    assert container._dependency_health.snapshot()["grafana"].up
    await container.stop()


async def test_entering_the_asgi_app_boots_real_tools_and_health_reports_ok() -> None:
    container = ToolboxContainer(make_settings())

    with TestClient(container.asgi_app, base_url="http://127.0.0.1:8001") as client:
        response = client.get(f"{ActuatorRouter.PREFIX}/health/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}
    assert {tool.name for tool in await container.mcp_server.list_tools()} == {
        "users_tables",
        "python_executor",
        "file_reader",
        "file_writer",
    }


async def test_stop_after_boot_does_not_raise() -> None:
    container = ToolboxContainer(make_settings())
    await container.boot()

    await container.stop()  # must not raise


async def test_booting_twice_runs_one_reconcile_loop() -> None:
    container = ToolboxContainer(make_settings())
    container.__dict__["_external_sources"] = [ExternalSource("grafana", FlakyServer())]

    await container.boot()
    first = container._reconciling
    await container.boot()

    assert container._reconciling is first
    await container.stop()
    assert first.cancelled()

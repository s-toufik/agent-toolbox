from agent_toolbox.application.port.outbound.tool_provider_port import ExternalSource
from bootstrap.container.toolbox_container import ToolboxContainer
from tests.agent_toolbox.stubs import Named, RecordingToolServer

INTERNAL_TOOLS = {"users_tables", "python_executor", "file_reader", "file_writer"}


class FlakyServer:
    def __init__(self) -> None:
        self.up = False

    async def tools(self):
        if not self.up:
            raise ConnectionError("refused")
        return [Named("grafana_search")]


def serving(container: ToolboxContainer, *scopes: str) -> dict[str, RecordingToolServer]:
    servers = {
        scope.name: RecordingToolServer() for scope in container.scopes if scope.name in scopes
    }
    container.serve(
        {scope: servers[scope.name] for scope in container.scopes if scope.name in scopes}
    )
    return servers


async def test_boot_binds_each_served_scope_s_tools(make_settings) -> None:
    container = ToolboxContainer(make_settings())
    servers = serving(container, "all", "coding")

    await container.boot()

    assert set(servers["all"].tools) == INTERNAL_TOOLS
    assert set(servers["coding"].tools) == {"python_executor", "file_reader", "file_writer"}
    await container.stop()


async def test_an_mcp_server_that_starts_after_the_toolbox_joins_it_without_a_restart(
    make_settings,
) -> None:
    container = ToolboxContainer(make_settings())
    grafana = FlakyServer()
    container._external_mcp.__dict__["sources"] = [ExternalSource("grafana", grafana)]
    servers = serving(container, "all", "observation")
    await container.boot()
    before = set(servers["observation"].tools)

    grafana.up = True
    await container._external_mcp.reconciler.reconcile()

    assert before == set()
    assert set(servers["observation"].tools) == {"grafana_search"}
    assert "grafana_search" in servers["all"].tools
    await container.stop()


async def test_the_actuator_is_ready_once_booted_and_reports_the_mcp_servers(make_settings) -> None:
    container = ToolboxContainer(make_settings(deployment_environment="homelab"))
    container._external_mcp.__dict__["sources"] = [ExternalSource("grafana", FlakyServer())]
    serving(container, "all")

    before = container.actuator.readiness().status
    await container.boot()
    health = container.actuator.health()

    assert (before, container.actuator.readiness().status) == ("DOWN", "UP")
    assert container.actuator.info().environment == "homelab"
    assert health.dependencies is not None
    assert health.dependencies["grafana"].status == "DOWN"
    assert health.dependencies["grafana"].error == "refused"
    await container.stop()


async def test_booting_twice_runs_one_reconcile_loop(make_settings) -> None:
    container = ToolboxContainer(make_settings())
    container._external_mcp.__dict__["sources"] = [ExternalSource("grafana", FlakyServer())]

    await container.boot()
    first = container._reconciling
    await container.boot()

    assert container._reconciling is first
    await container.stop()
    assert first.cancelled()

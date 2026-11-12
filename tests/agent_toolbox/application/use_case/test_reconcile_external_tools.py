import asyncio
import contextlib

from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.application.port.outbound.tool_publisher_port import CatalogChange
from agent_toolbox.application.use_case.reconcile_external_tools import (
    ExternalSource,
    ReconcileExternalTools,
)
from agent_toolbox.domain.model.dependency_health import DependencyHealth
from agent_toolbox.domain.model.refresh_policy import RefreshPolicy
from tests.agent_toolbox.stubs import Named


class Server:
    def __init__(self, *tool_names: str, up: bool = True) -> None:
        self.tool_names = list(tool_names)
        self.up = up

    async def tools(self):
        if not self.up:
            raise ConnectionError("refused")
        return [Named(name) for name in self.tool_names]


class Publisher:
    def __init__(self) -> None:
        self.changes: list[CatalogChange] = []

    def publish(self, change: CatalogChange) -> None:
        self.changes.append(change)


def reconciler(logger, **servers: Server):
    catalog = ToolCatalog([Named("file_reader")])
    health = DependencyHealth()
    publisher = Publisher()
    use_case = ReconcileExternalTools(
        [ExternalSource(name, server) for name, server in servers.items()], catalog, health, logger
    )
    use_case.publish_to(publisher)
    return use_case, catalog, health, publisher


async def test_a_server_down_at_start_gets_its_tools_once_it_is_back(logger) -> None:
    grafana = Server("grafana_search", up=False)
    use_case, catalog, health, publisher = reconciler(logger, grafana=grafana)

    assert await use_case.reconcile() is False
    assert [tool.name for tool in catalog.tools] == ["file_reader"]

    grafana.up = True
    assert await use_case.reconcile() is True

    assert [tool.name for tool in catalog.tools] == ["file_reader", "grafana_search"]
    assert [tool.name for tool in publisher.changes[0].added] == ["grafana_search"]
    assert health.snapshot()["grafana"].up
    assert "External MCP 'grafana' is back" in logger.messages("info")


async def test_a_server_that_goes_down_keeps_its_tools_and_warns_once(logger) -> None:
    mongodb = Server("mongodb_find")
    use_case, catalog, health, publisher = reconciler(logger, mongodb=mongodb)
    await use_case.reconcile()

    mongodb.up = False
    await use_case.reconcile()
    await use_case.reconcile()

    assert catalog.get("mongodb_find") is not None
    assert len(publisher.changes) == 1
    assert health.snapshot()["mongodb"].error == "refused"
    assert len([m for m in logger.messages("warning") if "'mongodb' unavailable" in m]) == 1


async def test_a_tool_the_server_no_longer_lists_is_removed(logger) -> None:
    postgres = Server("postgres_query", "postgres_explain")
    use_case, catalog, _, publisher = reconciler(logger, postgres=postgres)
    await use_case.reconcile()

    postgres.tool_names = ["postgres_query"]
    await use_case.reconcile()

    assert publisher.changes[-1].removed == ("postgres_explain",)
    assert catalog.get("postgres_explain") is None


async def run_until(use_case: ReconcileExternalTools, stop: asyncio.Event) -> None:
    task = asyncio.create_task(use_case.run())
    await asyncio.wait_for(stop.wait(), timeout=1)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


async def test_the_loop_sleeps_by_the_backoff_and_resets_when_the_server_is_back(logger) -> None:
    grafana = Server("grafana_search", up=False)
    delays: list[float] = []
    stop = asyncio.Event()

    async def sleep(seconds: float) -> None:
        delays.append(seconds)
        if len(delays) == 3:
            grafana.up = True
        if len(delays) == 5:
            stop.set()
            await asyncio.Event().wait()

    catalog, health = ToolCatalog(), DependencyHealth()
    use_case = ReconcileExternalTools(
        [ExternalSource("grafana", grafana)], catalog, health, logger, sleep=sleep
    )
    await use_case.reconcile()

    await run_until(use_case, stop)

    assert delays == [5, 10, 20, 60, 60]
    assert catalog.get("grafana_search") is not None


async def test_each_server_keeps_its_own_pace(logger) -> None:
    delays: list[float] = []
    stop = asyncio.Event()

    async def sleep(seconds: float) -> None:
        delays.append(seconds)
        if len(delays) == 8:
            stop.set()
        await asyncio.sleep(0)

    health = DependencyHealth()
    use_case = ReconcileExternalTools(
        [
            ExternalSource("grafana", Server("grafana_search", up=False), RefreshPolicy(60, 7, 28)),
            ExternalSource("mongodb", Server("mongodb_find"), RefreshPolicy(33, 5, 60)),
        ],
        ToolCatalog(),
        health,
        logger,
        sleep=sleep,
    )
    await use_case.reconcile()

    await run_until(use_case, stop)

    assert set(delays) <= {7, 14, 28, 33}
    assert {7, 14, 33} <= set(delays)


async def test_without_external_servers_there_is_no_loop(logger) -> None:
    use_case, *_ = reconciler(logger)

    await asyncio.wait_for(use_case.run(), timeout=1)

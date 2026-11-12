import asyncio
from collections.abc import Awaitable, Callable, Sequence

from pycraftcore.logger.port import Logger

from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.application.port.outbound.tool_provider_port import ExternalSource
from agent_toolbox.application.port.outbound.tool_publisher_port import (
    CatalogChange,
    ToolPublisher,
)
from agent_toolbox.domain.model.dependency_health import DependencyHealth


class ReconcileExternalTools:
    def __init__(
        self,
        sources: Sequence[ExternalSource],
        catalog: ToolCatalog,
        health: DependencyHealth,
        logger: Logger,
        describe_error: Callable[[BaseException], str] = str,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._sources = tuple(sources)
        self._catalog = catalog
        self._health = health
        self._logger = logger
        self._describe_error = describe_error
        self._sleep = sleep
        self._publisher: ToolPublisher | None = None

    def publish_to(self, publisher: ToolPublisher) -> None:
        self._publisher = publisher

    async def reconcile(self) -> bool:
        for source in self._sources:
            await self._reconcile(source)
        return self._health.all_up

    async def run(self) -> None:
        async with asyncio.TaskGroup() as group:
            for source in self._sources:
                group.create_task(self._keep_reconciling(source), name=f"reconcile-{source.name}")

    async def _keep_reconciling(self, source: ExternalSource) -> None:
        failures: int = 0 if self._health.is_up(source.name) else 1
        while True:
            await self._sleep(source.policy.delay_after(failures))
            failures = 0 if await self._reconcile(source) else failures + 1

    async def _reconcile(self, source: ExternalSource) -> bool:
        try:
            tools: list[Tool] = await source.provider.tools()
        except Exception as exception:
            if self._health.down(source.name, self._describe_error(exception)):
                self._logger.warning(
                    f"External MCP '{source.name}' unavailable; its tools stay listed and fail "
                    f"until it is back: {self._describe_error(exception)}"
                )
            return False

        came_back: bool = self._health.up(source.name)
        change: CatalogChange = self._catalog.replace(source.name, tools)
        if came_back:
            self._logger.info(f"External MCP '{source.name}' is back")
        if change.conflicts:
            self._logger.warning(
                f"External MCP '{source.name}': tools skipped, their names are taken: "
                f"{', '.join(change.conflicts)}"
            )
        if change:
            self._logger.info(
                f"External MCP '{source.name}': {len(tools) - len(change.conflicts)} tools"
                f"{_listed(' added', [tool.name for tool in change.added])}"
                f"{_listed(' removed', list(change.removed))}"
            )
            if self._publisher is not None:
                self._publisher.publish(change)
        return True


def _listed(label: str, names: list[str]) -> str:
    return f";{label}: {', '.join(names)}" if names else ""

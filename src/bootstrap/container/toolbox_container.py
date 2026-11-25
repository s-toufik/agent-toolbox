import asyncio
from collections.abc import Mapping
from contextlib import suppress
from functools import cached_property

from pycraftcore.application_configuration.model import McpConnector
from pycraftcore.jwt import TokenVerifier
from pycraftcore.logger.port import Logger
from pycraftcore.mcp import ToolServer
from pycraftcore.web.actuator import Actuator, DependencyReport, HealthStatus

from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from agent_toolbox.adapter.inbound.mcp.tool_publisher import McpToolPublisher
from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.application.use_case.issue_token_usecase import IssueTokenUseCase
from agent_toolbox.domain.model.tool_scope import ToolScope
from bootstrap.application.application_metadata import (
    APPLICATION_AUTHORS,
    APPLICATION_NAME,
    APPLICATION_VERSION,
)
from bootstrap.configuration.settings import ProcessSettings
from bootstrap.di.toolbox_di import ToolboxDI


class ToolboxContainer(ToolboxDI):
    def __init__(self, settings: ProcessSettings) -> None:
        super().__init__(settings)
        self._servers: dict[ToolScope, ToolServer] = {}

    @property
    def logging(self) -> Logger:
        return self._logging

    @property
    def settings(self) -> ProcessSettings:
        return self._settings

    @property
    def scopes(self) -> tuple[ToolScope, ...]:
        return self._scopes.declared

    @property
    def self_connector(self) -> McpConnector:
        return self._scopes.self_connector

    @property
    def token_verifier(self) -> TokenVerifier:
        return self._auth.tokens

    @property
    def issue_token(self) -> IssueTokenUseCase:
        return self._auth.issue_token

    @cached_property
    def actuator(self) -> Actuator:
        return Actuator(
            APPLICATION_NAME,
            APPLICATION_VERSION,
            self._settings.deployment_environment,
            APPLICATION_AUTHORS,
            is_ready=lambda: bool(self._tool_catalog.tools),
            dependencies=self._dependency_reports,
        )

    def serve(self, servers: Mapping[ToolScope, ToolServer]) -> None:
        self._servers = dict(servers)

    async def boot(self) -> None:
        _ = self._telemetry_provider
        reconciler = self._external_mcp.reconciler
        for scope, server in self._servers.items():
            tools = await self._scope_tools(scope)
            binder = ToolBinder(InvokeToolUseCase(tools, self._logging))
            bound: list[str] = binder.bind(server)
            self._logging.info(f"Tools of scope '{scope.name}': {', '.join(bound)}")
            reconciler.publish_to(
                McpToolPublisher(
                    server, binder, tools, refreshed=(ExecutePython.name,), scope=scope
                )
            )
        if "_reconciling" not in self.__dict__:
            self._reconciling = asyncio.create_task(
                reconciler.run(), name="external-mcp-reconciler"
            )
        self._logging.info("Toolbox container booted")

    async def stop(self) -> None:
        reconciling: asyncio.Task[None] | None = self.__dict__.pop("_reconciling", None)
        if reconciling is not None:
            reconciling.cancel()
            with suppress(asyncio.CancelledError):
                await reconciling
        await self._stop_factories()
        await self._shutdown_telemetry()
        self._logging.info("Toolbox container shut down")

    def _dependency_reports(self) -> dict[str, DependencyReport]:
        return {
            name: DependencyReport(
                HealthStatus.UP if state.up else HealthStatus.DOWN,
                state.since.isoformat(timespec="seconds"),
                state.error,
            )
            for name, state in self._external_mcp.health.snapshot().items()
        }

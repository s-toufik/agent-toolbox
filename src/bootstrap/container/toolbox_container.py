import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from functools import cached_property

from mcp.server.mcpserver import MCPServer
from pycraftcore.application_configuration import ApplicationConfiguration
from pycraftcore.logger.port import Logger
from starlette.applications import Starlette

from agent_toolbox.adapter.inbound.mcp.actuator import ActuatorRouter
from agent_toolbox.adapter.inbound.mcp.mcp_asgi_factory import (
    build_mcp_asgi_app,
    mcp_base_path,
    scope_path,
)
from agent_toolbox.adapter.inbound.mcp.mcp_server_factory import build_mcp_server
from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from agent_toolbox.adapter.inbound.mcp.tool_publisher import McpToolPublisher
from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from agent_toolbox.application.catalog.scoped_tool_catalog import ScopedToolCatalog
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.model.tool_scope import ALL_TOOLS, ToolScope
from bootstrap.di.toolbox_di import ToolboxDI
from src import (
    APPLICATION_AUTHORS_EMAIL,
    APPLICATION_DEPLOYMENT_ENVIRONMENT,
    APPLICATION_NAME,
    APPLICATION_VERSION,
)

SERVER_NAME: str = "toolbox"
SERVER_VERSION: str = "1.0.0"
INSTRUCTIONS: str = "Analytics toolbox"


class ToolboxContainer(ToolboxDI):
    @property
    def logging(self) -> Logger:
        return self._logging

    @property
    def application_configuration(self) -> ApplicationConfiguration:
        return self._configuration

    @cached_property
    def mcp_server(self) -> MCPServer:
        return self.mcp_servers[ALL_TOOLS]

    @cached_property
    def mcp_servers(self) -> dict[ToolScope, MCPServer]:
        servers: dict[ToolScope, MCPServer] = {}
        for scope in self._scopes:
            server: MCPServer = build_mcp_server(
                name=SERVER_NAME if scope.is_all else f"{SERVER_NAME}-{scope.name}",
                version=SERVER_VERSION,
                instructions=INSTRUCTIONS,
                lifespan=self._lifespan if scope.is_all else None,
            )
            servers[scope] = server
        ActuatorRouter(
            server=servers[ALL_TOOLS],
            app_name=APPLICATION_NAME,
            app_version=APPLICATION_VERSION,
            app_deployment_environment=APPLICATION_DEPLOYMENT_ENVIRONMENT,
            app_authors=APPLICATION_AUTHORS_EMAIL,
            dependencies=self._dependency_health.snapshot,
        ).register_actuator_routes()
        return servers

    @cached_property
    def asgi_app(self) -> Starlette:
        return build_mcp_asgi_app(self.mcp_servers, self._self_connector)

    @asynccontextmanager
    async def _lifespan(self, server: MCPServer) -> AsyncGenerator[None]:
        await self.boot()
        try:
            yield
        finally:
            await self.stop()

    async def boot(self) -> None:
        _ = self._telemetry_provider
        reconciler = self._external_tools_reconciler
        base_path: str = mcp_base_path(self._self_connector)
        for scope, server in self.mcp_servers.items():
            tools: ScopedToolCatalog = await self._scope_tools(scope)
            binder = ToolBinder(InvokeToolUseCase(tools, self._logging))
            bound = binder.bind(server)
            self.logging.info(
                f"Tools of scope '{scope.name}' at {scope_path(base_path, scope)}: {', '.join(bound)}"
            )
            reconciler.publish_to(
                McpToolPublisher(
                    server, binder, tools, refreshed=(ExecutePython.name,), scope=scope
                )
            )
        if "_reconciling" not in self.__dict__:
            self._reconciling = asyncio.create_task(
                reconciler.run(), name="external-mcp-reconciler"
            )
        self.logging.info("Toolbox container booted")

    async def stop(self) -> None:
        reconciling: asyncio.Task[None] | None = self.__dict__.pop("_reconciling", None)
        if reconciling is not None:
            reconciling.cancel()
            with suppress(asyncio.CancelledError):
                await reconciling
        await self._stop_factories()
        await self._shutdown_telemetry()
        self.logging.info("Toolbox container shut down")

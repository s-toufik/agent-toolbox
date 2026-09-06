from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import cached_property

from mcp.server.mcpserver import MCPServer
from pycraftcore.application_configuration import ApplicationConfiguration
from pycraftcore.application_configuration.model.connector import McpConnector
from pycraftcore.logger.port import Logger
from starlette.applications import Starlette

from agent_toolbox.adapter.inbound.mcp.actuator import ActuatorRouter
from agent_toolbox.adapter.inbound.mcp.mcp_asgi_factory import build_mcp_asgi_app
from agent_toolbox.adapter.inbound.mcp.mcp_server_factory import build_mcp_server
from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from bootstrap.di.toolbox_di import ToolboxDI
from src import (
    APPLICATION_API_ROOT_PATH,
    APPLICATION_AUTHORS_EMAIL,
    APPLICATION_DEPLOYMENT_ENVIRONMENT,
    APPLICATION_NAME,
    APPLICATION_VERSION,
)

SERVER_NAME: str = "toolbox"
SERVER_VERSION: str = "1.0.0"
SELF_CONNECTOR_NAME: str = "self"


class ToolboxContainer(ToolboxDI):
    @property
    def logging(self) -> Logger:
        return self._logging

    @property
    def application_configuration(self) -> ApplicationConfiguration:
        return self._configuration

    @cached_property
    def mcp_server(self) -> MCPServer:
        server: MCPServer = build_mcp_server(
            name=SERVER_NAME,
            version=SERVER_VERSION,
            instructions=(
                "Analytics toolbox: sandboxed Python execution and read-only SQL "
                "against the service database."
            ),
            lifespan=self._lifespan,
        )

        ActuatorRouter(
            server=server,
            app_name=APPLICATION_NAME,
            app_version=APPLICATION_VERSION,
            app_deployment_environment=APPLICATION_DEPLOYMENT_ENVIRONMENT,
            app_api_root_path=APPLICATION_API_ROOT_PATH,
            app_authors=APPLICATION_AUTHORS_EMAIL,
        ).register_actuator_routes()

        return server

    @cached_property
    def asgi_app(self) -> Starlette:
        connector: McpConnector = self._configuration.connector.mcp(SELF_CONNECTOR_NAME)
        return build_mcp_asgi_app(self.mcp_server, connector)

    @asynccontextmanager
    async def _lifespan(self, server: MCPServer) -> AsyncIterator[None]:
        await self.boot(server)
        try:
            yield
        finally:
            await self.stop()

    async def boot(self, server: MCPServer | None = None) -> None:
        target = server or self.mcp_server
        registry = await self._tool_registry()
        binder = ToolBinder(self._execute_tool_use_case(registry), registry)
        bound = binder.bind(target)
        self.logging.info(f"Toolbox container booted, tools exposed: {', '.join(bound)}")

    async def stop(self) -> None:
        await self._stop_factories()
        await self._shutdown_telemetry()
        self.logging.info("Toolbox container shut down")

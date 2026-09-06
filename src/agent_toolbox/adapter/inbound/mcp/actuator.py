from mcp.server import MCPServer
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from agent_toolbox.adapter.inbound.enum.status import HealthStatus
from agent_toolbox.adapter.inbound.schema.response import HealthSchema, InfoSchema


class ActuatorRouter:
    PREFIX = "/actuator"

    def __init__(
        self,
        server: MCPServer,
        app_name: str,
        app_version: str,
        app_deployment_environment: str,
        app_api_root_path: str,
        app_authors: str,
    ) -> None:
        self._server = server
        self._app_name = app_name
        self._app_version = app_version
        self._app_deployment_environment = app_deployment_environment
        self._app_authors = app_authors
        self._app_root_path = app_api_root_path

    async def _is_ready(self) -> bool:
        return bool(await self._server.list_tools())

    def register_actuator_routes(self) -> None:

        @self._server.custom_route(f"{self._app_root_path}{self.PREFIX}/health", methods=["GET"])
        async def _health(_: Request) -> JSONResponse:
            return JSONResponse(content=HealthSchema(status=HealthStatus.UP).model_dump())

        @self._server.custom_route(
            f"{self._app_root_path}{self.PREFIX}/health/liveness", methods=["GET"]
        )
        async def _liveness(_: Request) -> JSONResponse:
            return JSONResponse(content=HealthSchema(status=HealthStatus.UP).model_dump())

        @self._server.custom_route(
            f"{self._app_root_path}{self.PREFIX}/health/readiness", methods=["GET"]
        )
        async def _readiness(_: Request) -> JSONResponse:
            if await self._is_ready():
                return JSONResponse(content=HealthSchema(status=HealthStatus.UP).model_dump())

            return JSONResponse(
                content=HealthSchema(status=HealthStatus.DOWN).model_dump(),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        @self._server.custom_route(f"{self._app_root_path}{self.PREFIX}/info", methods=["GET"])
        async def _info(_: Request) -> JSONResponse:
            return JSONResponse(
                content=InfoSchema(
                    name=self._app_name,
                    version=self._app_version,
                    environment=self._app_deployment_environment,
                    api_root_path=self._app_root_path,
                    authors=self._app_authors,
                ).model_dump()
            )

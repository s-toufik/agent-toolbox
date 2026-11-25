import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from pycraftcore.mcp_sdk import SdkToolServer, create_app, create_server, mcp_path
from pycraftcore.web.middleware import BearerTokenMiddleware
from pycraftcore.web.schema import ApiSettings
from pycraftcore.web_starlette import actuator_router
from starlette.applications import Starlette
from starlette.middleware import Middleware

from agent_toolbox.domain.model.tool_scope import ToolScope
from bootstrap.application.application_metadata import APPLICATION_NAME, APPLICATION_VERSION
from bootstrap.application.mcp_sdk.token_route import token_route
from bootstrap.container.toolbox_container import ToolboxContainer

SERVER_NAME: str = "toolbox"


def create_mcp_sdk_app(container: ToolboxContainer) -> Starlette:
    connector = container.self_connector
    base_path: str = mcp_path(connector)
    servers = {
        scope: create_server(name=_server_name(scope), version=APPLICATION_VERSION)
        for scope in container.scopes
    }
    container.serve({scope: SdkToolServer(server) for scope, server in servers.items()})
    return create_app(
        ApiSettings(title=APPLICATION_NAME, version=APPLICATION_VERSION),
        {_scope_path(base_path, scope): server for scope, server in servers.items()},
        connector,
        routes=[actuator_router(container.actuator), token_route(container.issue_token)],
        middleware=[
            Middleware(
                BearerTokenMiddleware, verifier=container.token_verifier, protected=[base_path]
            )
        ],
        lifespan=lambda: _running(container),
        allowed_hosts=container.settings.extra_allowed_hosts,
    )


def _server_name(scope: ToolScope) -> str:
    return SERVER_NAME if scope.is_all else f"{SERVER_NAME}-{scope.name}"


def _scope_path(base_path: str, scope: ToolScope) -> str:
    return base_path if scope.is_all else f"{base_path}/{scope.name}"


@asynccontextmanager
async def _running(container: ToolboxContainer) -> AsyncGenerator[None]:
    try:
        await container.boot()
    except Exception as exception:
        container.logging.critical(
            "Toolbox container failed to boot:\n" + "".join(traceback.format_exception(exception))
        )
        raise
    try:
        yield
    finally:
        await container.stop()

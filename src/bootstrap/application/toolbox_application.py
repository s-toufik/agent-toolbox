from pycraftcore.web.asgi import ASGIApp

from bootstrap.application.mcp_sdk.mcp_sdk_app import create_mcp_sdk_app
from bootstrap.configuration.settings import ProcessSettings
from bootstrap.container.toolbox_container import ToolboxContainer


def create_toolbox_application(settings: ProcessSettings | None = None) -> ASGIApp:
    return create_mcp_sdk_app(ToolboxContainer(settings or ProcessSettings.for_role("toolbox")))

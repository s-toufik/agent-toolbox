from starlette.applications import Starlette

from bootstrap.configuration.settings import ProcessSettings
from bootstrap.container.toolbox_container import ToolboxContainer


def create_toolbox_application(settings: ProcessSettings | None = None) -> Starlette:
    process_settings = settings or ProcessSettings.for_role("toolbox")
    container = ToolboxContainer(process_settings)
    return container.asgi_app


app: Starlette = create_toolbox_application()

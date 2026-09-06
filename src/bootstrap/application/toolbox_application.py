from starlette.applications import Starlette

from bootstrap.configuration.settings import ProcessSettings
from bootstrap.container.toolbox_container import ToolboxContainer

DEFAULT_PORT: int = 8001


def create_toolbox_application(settings: ProcessSettings | None = None) -> Starlette:
    process_settings = settings or ProcessSettings.for_role("toolbox", DEFAULT_PORT)
    container = ToolboxContainer(process_settings)
    return container.asgi_app


app: Starlette = create_toolbox_application()


def main() -> None:
    import uvicorn

    settings = ProcessSettings.for_role("toolbox", DEFAULT_PORT)
    uvicorn.run(
        "bootstrap.application.toolbox_application:app",
        host=settings.host,
        port=settings.port,
    )

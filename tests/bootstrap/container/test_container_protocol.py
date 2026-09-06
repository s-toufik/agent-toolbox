from pathlib import Path

from bootstrap.configuration.settings import ProcessSettings
from bootstrap.container.container import Container
from bootstrap.container.toolbox_container import ToolboxContainer

REAL_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


def test_toolbox_container_satisfies_the_container_protocol() -> None:
    settings = ProcessSettings(
        role="toolbox",
        environment="debug",
        configuration_directory=REAL_CONFIG_DIR,
        host="0.0.0.0",
        port=8001,
    )

    assert isinstance(ToolboxContainer(settings), Container)

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from agent_toolbox.adapter.inbound.mcp.actuator import ActuatorRouter
from bootstrap.application.toolbox_application import create_toolbox_application
from bootstrap.configuration.settings import ProcessSettings

REAL_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


@pytest.fixture(autouse=True)
def _base_env(monkeypatch, tmp_path):
    monkeypatch.setenv("USER_DB_HOST", str(tmp_path))
    monkeypatch.setenv("USER_DB_NAME", "users")
    monkeypatch.setenv("CHECKPOINT_DB_HOST", str(tmp_path))
    monkeypatch.setenv("CHECKPOINT_DB_NAME", "checkpoint")
    monkeypatch.setenv("TOOLBOX_URL", "http://127.0.0.1:8001/mcp")


def make_settings() -> ProcessSettings:
    return ProcessSettings(
        role="toolbox",
        environment="debug",
        configuration_directory=REAL_CONFIG_DIR,
    )


def test_the_returned_app_is_the_containers_own_mcp_asgi_app_and_boots_real_tools() -> None:
    app = create_toolbox_application(settings=make_settings())

    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        response = client.get(f"{ActuatorRouter.PREFIX}/health/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}

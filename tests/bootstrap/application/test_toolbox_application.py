from pathlib import Path

import pytest
import uvicorn as uvicorn_module
from starlette.testclient import TestClient

from bootstrap.application.toolbox_application import create_toolbox_application, main
from bootstrap.configuration.settings import ProcessSettings
from src import APPLICATION_API_ROOT_PATH

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
        host="0.0.0.0",
        port=8001,
    )


def test_the_returned_app_is_the_containers_own_mcp_asgi_app_and_boots_real_tools() -> None:
    app = create_toolbox_application(settings=make_settings())

    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        response = client.get(f"{APPLICATION_API_ROOT_PATH}/actuator/health/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_main_runs_uvicorn_with_the_configured_host_and_port(monkeypatch) -> None:
    monkeypatch.setenv("TOOLBOX_HOST", "127.0.0.1")
    monkeypatch.setenv("TOOLBOX_PORT", "9998")
    calls: list[dict] = []

    def fake_run(target, **kwargs):
        calls.append({"target": target, **kwargs})

    monkeypatch.setattr(uvicorn_module, "run", fake_run)

    main()

    assert calls == [
        {
            "target": "bootstrap.application.toolbox_application:app",
            "host": "127.0.0.1",
            "port": 9998,
        }
    ]

from collections.abc import Callable
from pathlib import Path

import pytest

from bootstrap.configuration.settings import ProcessSettings
from bootstrap.di.toolbox_di import ToolboxDI

REAL_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
EXTERNAL_MCP_URLS: tuple[str, ...] = ("GRAFANA_MCP_URL", "MONGODB_MCP_URL", "POSTGRES_MCP_URL")


@pytest.fixture
def toolbox_env(monkeypatch, tmp_path) -> Path:
    monkeypatch.setenv("USER_DB_HOST", str(tmp_path))
    monkeypatch.setenv("USER_DB_NAME", "users")
    monkeypatch.setenv("TOOLBOX_URL", "http://127.0.0.1:8001/mcp")
    return tmp_path


@pytest.fixture
def make_settings(toolbox_env) -> Callable[..., ProcessSettings]:
    def make(**overrides) -> ProcessSettings:
        values = {
            "role": "toolbox",
            "environment": "debug",
            "configuration_directory": REAL_CONFIG_DIR,
            "jwt_key": "k" * 32,
            "jwt_username": "toufik",
        }
        return ProcessSettings(**values | overrides)

    return make


@pytest.fixture
def make_di(make_settings) -> Callable[..., ToolboxDI]:
    return lambda **overrides: ToolboxDI(make_settings(**overrides))


@pytest.fixture
def without_external_mcp(monkeypatch) -> None:
    for variable in EXTERNAL_MCP_URLS:
        monkeypatch.delenv(variable, raising=False)

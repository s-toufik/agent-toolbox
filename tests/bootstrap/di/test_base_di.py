from pycraftcore.logger.enum import LogLevel

import bootstrap.di.base_di as base_di_module
from bootstrap.di.base_di import BaseDI
from tests.support.null_telemetry import NullTelemetryProvider


class RecordingRepository:
    def __init__(self) -> None:
        self.connected = False
        self.disconnected = False

    async def connection(self):
        raise AssertionError("not expected to be called")

    async def connect(self) -> RecordingRepository:
        self.connected = True
        return self

    async def disconnect(self) -> None:
        self.disconnected = True

    async def execute(self, sql: str, parameters: tuple = ()) -> list[dict]:
        raise AssertionError("not expected to be called")


def test_register_repository_returns_the_same_object_and_tracks_it(make_settings) -> None:
    di = BaseDI(make_settings())
    repository = RecordingRepository()

    assert di._register_repository(repository) is repository
    assert di._repositories == [repository]


async def test_stop_factories_disconnects_repositories(make_settings) -> None:
    di = BaseDI(make_settings())
    repository = RecordingRepository()
    di._register_repository(repository)

    await di._stop_factories()

    assert repository.disconnected


def test_configuration_loads_the_real_tree(make_settings) -> None:
    di = BaseDI(make_settings())

    assert di._configuration.connector.mcp("self").transport == "streamable_http"


def test_loading_the_configuration_applies_its_log_level_first(make_settings, monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    applied: list[str] = []
    monkeypatch.setattr(base_di_module, "configure_logging", applied.append)
    di = BaseDI(make_settings())

    _ = di._configuration

    assert applied == [LogLevel.WARNING]


def test_telemetry_provider_service_name_is_derived_from_the_role(make_settings) -> None:
    di = BaseDI(make_settings(role="toolbox"))

    provider = di._telemetry_provider

    assert isinstance(provider, NullTelemetryProvider)
    assert provider.service_name == "toolbox-service"


async def test_shutdown_telemetry_is_a_no_op_when_never_constructed(make_settings) -> None:
    di = BaseDI(make_settings())

    await di._shutdown_telemetry()  # must not raise


async def test_shutdown_telemetry_shuts_down_and_evicts_the_cached_provider(make_settings) -> None:
    di = BaseDI(make_settings())
    provider = di._telemetry_provider  # force construction
    assert isinstance(provider, NullTelemetryProvider)
    assert "_telemetry_provider" in di.__dict__

    await di._shutdown_telemetry()

    assert provider.is_shut_down
    assert "_telemetry_provider" not in di.__dict__

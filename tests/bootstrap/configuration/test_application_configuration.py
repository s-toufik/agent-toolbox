import pytest

from bootstrap.configuration.application_configuration import SetApplicationConfiguration


def test_loads_the_real_configuration_tree(make_settings, logger) -> None:
    configuration = SetApplicationConfiguration(make_settings(), logger)()

    assert configuration.connector.mcp("self").transport == "streamable_http"
    assert configuration.connector.database("users").engine == "sqlite"
    assert logger.messages("info")[0].startswith("Loading 'toolbox' schema (debug) from")


def test_a_missing_configuration_directory_is_reported(make_settings, logger, tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        SetApplicationConfiguration(
            make_settings(configuration_directory=tmp_path / "none"), logger
        )()

    assert logger.messages("critical")

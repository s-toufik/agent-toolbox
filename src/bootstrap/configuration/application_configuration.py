from pycraftcore.application_configuration import ApplicationConfiguration
from pycraftcore.application_configuration.adapter import (
    LoadApplicationConfiguration,
    OmegaConfigurationReader,
)
from pycraftcore.application_configuration.enum import RunTypeEnvironment
from pycraftcore.logger.port import Logger

from bootstrap.configuration.settings import ProcessSettings


class SetApplicationConfiguration:
    def __init__(self, settings: ProcessSettings, logger: Logger) -> None:
        self._settings = settings
        self._logger = logger

    def __call__(self) -> ApplicationConfiguration:
        environment = RunTypeEnvironment(self._settings.environment)
        directory = self._settings.configuration_directory
        self._logger.info(
            f"Loading '{self._settings.role}' schema ({environment.value}) from {directory}"
        )
        reader = OmegaConfigurationReader(environment, directory)
        return LoadApplicationConfiguration(reader, self._logger).load()

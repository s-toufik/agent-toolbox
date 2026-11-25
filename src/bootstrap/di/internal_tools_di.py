from collections.abc import Callable

from pycraftcore.application_configuration import ApplicationConfiguration
from pycraftcore.application_configuration.model import DatabaseOperation
from pycraftcore.file_handler.adapter import Handler
from pycraftcore.query_language.adapter import SqlHandlerFactory
from pycraftcore.repository.adapter import SqliteRepositoryFactory, SqliteSettingsMapper
from pycraftcore.repository.port import AsyncRepository, AsyncRepositoryFactory

from agent_toolbox.adapter.outbound.file.reader_tool import ReadFile
from agent_toolbox.adapter.outbound.file.writer_tool import WriteFile
from agent_toolbox.adapter.outbound.sql.sql_tool import QueryUsers
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.model.working_directory import WorkingDirectory

USERS_OPERATION_NAME: str = "users"


class InternalToolsDI:
    def __init__(
        self,
        configuration: ApplicationConfiguration,
        working_directory: WorkingDirectory | None,
        register_repository: Callable[[AsyncRepositoryFactory], AsyncRepositoryFactory],
    ) -> None:
        self._configuration = configuration
        self._working_directory = working_directory
        self._register_repository = register_repository

    async def tools(self) -> tuple[Tool, ...]:
        return (
            QueryUsers(await self._sqlite_repository(USERS_OPERATION_NAME), SqlHandlerFactory()),
            ReadFile(Handler, self._working_directory),
            WriteFile(Handler, self._working_directory),
        )

    async def _sqlite_repository(self, operation_name: str) -> AsyncRepository:
        operation: DatabaseOperation = self._configuration.operation.database(operation_name)
        factory: AsyncRepositoryFactory = SqliteRepositoryFactory(SqliteSettingsMapper(operation)())
        self._register_repository(factory)
        return await factory.connect()

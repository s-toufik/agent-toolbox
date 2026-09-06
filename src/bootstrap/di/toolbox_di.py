import asyncio

from pycraftcore.application_configuration.model.connector import DatabaseConnector
from pycraftcore.file_handler.adapter import Handler
from pycraftcore.query_language.adapter import SqlHandlerFactory
from pycraftcore.repository.adapter import SQLiteRepositoryFactory, SqliteSettingsMapper
from pycraftcore.repository.port import AsyncRepository, AsyncRepositoryFactory
from pycraftcore.runtime.adapter import PythonSafeCodeFactory
from pycraftcore.runtime.configuration import SafeCodeSettings

from agent_toolbox.adapter.outbound.code.python_tool import PythonTool
from agent_toolbox.adapter.outbound.file.reader_tool import FileReaderTool
from agent_toolbox.adapter.outbound.file.writer_tool import FileWriterTool
from agent_toolbox.adapter.outbound.registry.in_memory_tool_registry import InMemoryToolRegistry
from agent_toolbox.adapter.outbound.specification import (
    file_reader,
    file_writer,
    python_sandbox,
    user_database,
)
from agent_toolbox.adapter.outbound.sql.sql_tool import SqlTool
from agent_toolbox.application.port.outbound.tool_port import ToolPort, ToolRegistryPort
from agent_toolbox.application.use_case.execute_tool_usecase import ExecuteToolUseCase
from bootstrap.di.base_di import BaseDI


class ToolboxDI(BaseDI):
    async def _tools(self) -> list[ToolPort]:
        return [
            await self._sql_tool(),
            self._python_tool(),
            self._file_reader_tool(),
            self._file_writer_tool(),
        ]

    async def _tool_registry(self) -> ToolRegistryPort:
        return InMemoryToolRegistry(await self._tools())

    def _execute_tool_use_case(self, registry: ToolRegistryPort) -> ExecuteToolUseCase:
        return ExecuteToolUseCase(registry, self._logging)

    async def _sql_tool(self) -> SqlTool:
        repository: AsyncRepository = await self._sqlite_repository(user_database.CONNECTOR_NAME)
        return SqlTool(
            repository=repository,
            query_factory=SqlHandlerFactory(),
            specification=user_database.SPECIFICATION,
            default_dialect=user_database.DIALECT,
        )

    @staticmethod
    def _python_tool() -> PythonTool:
        settings = SafeCodeSettings(
            code_timeout=python_sandbox.TIMEOUT_SECONDS,
            max_memory_mb=python_sandbox.MAX_MEMORY_MB,
        )
        return PythonTool(
            code_factory=PythonSafeCodeFactory(settings=settings),
            specification=python_sandbox.SPECIFICATION,
            semaphore=asyncio.Semaphore(python_sandbox.MAX_CONCURRENCY),
        )

    @staticmethod
    def _file_reader_tool() -> FileReaderTool:
        return FileReaderTool(
            file_handler_provider=Handler,
            specification=file_reader.SPECIFICATION,
        )

    @staticmethod
    def _file_writer_tool() -> FileWriterTool:
        return FileWriterTool(
            file_handler_provider=Handler,
            specification=file_writer.SPECIFICATION,
        )

    async def _sqlite_repository(self, connector_name: str) -> AsyncRepository:
        connector: DatabaseConnector = self._configuration.connector.database(connector_name)
        factory: AsyncRepositoryFactory = SQLiteRepositoryFactory(SqliteSettingsMapper(connector)())
        self._register_repository(factory)
        return await factory.connect()

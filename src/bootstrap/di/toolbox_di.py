import asyncio
import secrets
from collections.abc import Callable
from pathlib import Path

from pycraftcore.application_configuration.model.connector import DatabaseConnector
from pycraftcore.file_handler.adapter import Handler
from pycraftcore.query_language.adapter import SqlHandlerFactory
from pycraftcore.repository.adapter import SqliteRepositoryFactory, SqliteSettingsMapper
from pycraftcore.repository.port import AsyncRepository, AsyncRepositoryFactory
from pycraftcore.runtime.adapter import PythonSafeCodeFactory
from pycraftcore.runtime.schema import SafeCodeSettings

from agent_toolbox.adapter.outbound.code.python_tool import PythonTool
from agent_toolbox.adapter.outbound.code.tool_bridge import ToolBridgeServer
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
from agent_toolbox.domain.model.tool_specification import ToolSpecification
from bootstrap.di.base_di import BaseDI


def _tool_signature(specification: ToolSpecification) -> str:
    arguments: list[str] = [
        parameter.name if parameter.required else f"{parameter.name}={parameter.default!r}"
        for parameter in specification.parameters
    ]

    return f"{specification.name}({', '.join(arguments)})"


def _tool_defaults(specification: ToolSpecification) -> dict[str, object]:
    return {
        parameter.name: parameter.default
        for parameter in specification.parameters
        if not parameter.required and parameter.default is not None
    }


class ToolboxDI(BaseDI):
    async def _tools(self) -> list[ToolPort]:
        data_tools: list[ToolPort] = [
            await self._sql_tool(),
            self._file_reader_tool(),
            self._file_writer_tool(),
        ]

        return [self._python_tool(data_tools), *data_tools]

    async def _tool_registry(self) -> ToolRegistryPort:
        return InMemoryToolRegistry(await self._tools())

    def _execute_tool_use_case(self, registry: ToolRegistryPort) -> ExecuteToolUseCase:
        return ExecuteToolUseCase(registry, self._logging)

    # ------------------------------------------------------------------------------------------- sql
    async def _sql_tool(self) -> SqlTool:
        repository: AsyncRepository = await self._sqlite_repository(user_database.CONNECTOR_NAME)
        return SqlTool(
            repository=repository,
            query_factory=SqlHandlerFactory(),
            specification=user_database.SPECIFICATION,
            default_dialect=user_database.DIALECT,
        )

    # ------------------------------------------------------------------------------------------- python
    def _python_tool(self, data_tools: list[ToolPort]) -> PythonTool:
        vault_directory: Path | None = self._settings.vault_directory
        vault_path: str | None = str(vault_directory) if vault_directory else None

        bridge_factory: Callable[[], ToolBridgeServer] | None = None
        tool_functions: tuple[str, ...] = ()
        if self._settings.sandbox_tool_access and data_tools:
            bridge_factory = self._sandbox_bridge_factory(data_tools)
            tool_functions = tuple(_tool_signature(tool.specification) for tool in data_tools)

        settings = SafeCodeSettings(
            code_timeout=python_sandbox.TIMEOUT_SECONDS,
            max_memory_mb=python_sandbox.MAX_MEMORY_MB,
            vault_path=vault_path,
        )
        return PythonTool(
            code_factory=PythonSafeCodeFactory(settings=settings),
            specification=python_sandbox.specification(vault_path, tool_functions),
            semaphore=asyncio.Semaphore(python_sandbox.MAX_CONCURRENCY),
            bridge_server_factory=bridge_factory,
        )

    def _sandbox_bridge_factory(self, data_tools: list[ToolPort]) -> Callable[[], ToolBridgeServer]:
        use_case = ExecuteToolUseCase(InMemoryToolRegistry(data_tools), self._logging)
        names: tuple[str, ...] = tuple(tool.specification.name for tool in data_tools)
        defaults: dict[str, dict[str, object]] = {
            tool.specification.name: _tool_defaults(tool.specification) for tool in data_tools
        }

        def factory() -> ToolBridgeServer:
            return ToolBridgeServer(use_case, names, secrets.token_hex(16), tool_defaults=defaults)

        return factory

    # ------------------------------------------------------------------------------------------- file reader
    @staticmethod
    def _file_reader_tool() -> FileReaderTool:
        return FileReaderTool(
            file_handler_provider=Handler,
            specification=file_reader.SPECIFICATION,
        )

    # ------------------------------------------------------------------------------------------- file writer
    @staticmethod
    def _file_writer_tool() -> FileWriterTool:
        return FileWriterTool(
            file_handler_provider=Handler,
            specification=file_writer.SPECIFICATION,
        )

    # ------------------------------------------------------------------------------------------- resources
    async def _sqlite_repository(self, connector_name: str) -> AsyncRepository:
        connector: DatabaseConnector = self._configuration.connector.database(connector_name)
        factory: AsyncRepositoryFactory = SqliteRepositoryFactory(SqliteSettingsMapper(connector)())
        self._register_repository(factory)
        return await factory.connect()

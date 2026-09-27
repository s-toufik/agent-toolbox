import asyncio
from pathlib import Path

from pycraftcore.application_configuration.model.connector import DatabaseConnector
from pycraftcore.file_handler.adapter import Handler
from pycraftcore.query_language.adapter import SqlHandlerFactory
from pycraftcore.repository.adapter import SqliteRepositoryFactory, SqliteSettingsMapper
from pycraftcore.repository.port import AsyncRepository, AsyncRepositoryFactory
from pycraftcore.runtime.adapter import PythonSafeCodeFactory
from pycraftcore.runtime.adapter.python.python_runner_template import PYTHON_ALLOWLIST
from pycraftcore.runtime.schema import SafeCodeSettings

from agent_toolbox.adapter.inbound.sandbox.tool_bridge import SandboxToolBridge
from agent_toolbox.adapter.inbound.tool_text import python_stub
from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from agent_toolbox.adapter.outbound.file.reader_tool import ReadFile
from agent_toolbox.adapter.outbound.file.writer_tool import WriteFile
from agent_toolbox.adapter.outbound.sandbox.python_sandbox import PythonSandbox
from agent_toolbox.adapter.outbound.sql.sql_tool import QueryUsers
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.model.working_directory import WorkingDirectory
from bootstrap.di.base_di import BaseDI

USERS_CONNECTOR_NAME: str = "users"

SANDBOX_TIMEOUT_SECONDS: int = 18000
SANDBOX_MAX_MEMORY_MB: int = 256
SANDBOX_MAX_CONCURRENCY: int = 8


class ToolboxDI(BaseDI):
    async def _invoke_tool_use_case(self) -> InvokeToolUseCase:
        working_directory: WorkingDirectory | None = self._working_directory()
        data_tools: list[Tool] = [
            QueryUsers(await self._sqlite_repository(USERS_CONNECTOR_NAME), SqlHandlerFactory()),
            ReadFile(Handler, working_directory),
            WriteFile(Handler, working_directory),
        ]
        return InvokeToolUseCase([self._execute_python(data_tools), *data_tools], self._logging)

    def _working_directory(self) -> WorkingDirectory | None:
        directory: Path | None = self._settings.working_directory
        return WorkingDirectory(str(directory)) if directory else None

    def _execute_python(self, data_tools: list[Tool]) -> ExecutePython:
        working_directory: WorkingDirectory | None = self._working_directory()
        root: str | None = working_directory.root if working_directory else None

        bridge: SandboxToolBridge | None = None
        if self._settings.sandbox_tool_access and data_tools:
            bridge = SandboxToolBridge(InvokeToolUseCase(data_tools, self._logging))

        settings = SafeCodeSettings(
            code_timeout=SANDBOX_TIMEOUT_SECONDS,
            max_memory_mb=SANDBOX_MAX_MEMORY_MB,
            working_directory=root,
        )
        sandbox = PythonSandbox(
            code_factory=PythonSafeCodeFactory(settings=settings),
            semaphore=asyncio.Semaphore(SANDBOX_MAX_CONCURRENCY),
            bridge_server=bridge.server if bridge else None,
        )
        return ExecutePython(
            sandbox,
            allowed_modules=PYTHON_ALLOWLIST,
            timeout_seconds=SANDBOX_TIMEOUT_SECONDS,
            working_directory=root,
            tool_signatures=[python_stub(tool) for tool in data_tools] if bridge else (),
        )

    async def _sqlite_repository(self, connector_name: str) -> AsyncRepository:
        connector: DatabaseConnector = self._configuration.connector.database(connector_name)
        factory: AsyncRepositoryFactory = SqliteRepositoryFactory(SqliteSettingsMapper(connector)())
        self._register_repository(factory)
        return await factory.connect()

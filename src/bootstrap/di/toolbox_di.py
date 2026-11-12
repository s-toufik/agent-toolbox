import asyncio
from collections.abc import Iterable, Mapping
from functools import cached_property
from pathlib import Path
from typing import Any

from pycraftcore.application_configuration.enum import ConnectorType
from pycraftcore.application_configuration.model.connector import DatabaseConnector, McpConnector
from pycraftcore.application_configuration.model.operation import McpOperation
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
from agent_toolbox.adapter.outbound.mcp.errors import root_causes
from agent_toolbox.adapter.outbound.mcp.mcp_tool_provider import McpToolProvider
from agent_toolbox.adapter.outbound.mcp.session_factory import McpSessionFactory
from agent_toolbox.adapter.outbound.sandbox.python_sandbox import PythonSandbox
from agent_toolbox.adapter.outbound.sql.sql_tool import QueryUsers
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.application.port.outbound.tool_lookup_port import ToolLookup
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.application.port.outbound.tool_provider_port import ExternalSource
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.application.use_case.reconcile_external_tools import ReconcileExternalTools
from agent_toolbox.domain.model.dependency_health import DependencyHealth
from agent_toolbox.domain.model.refresh_policy import RefreshPolicy
from agent_toolbox.domain.model.working_directory import WorkingDirectory
from bootstrap.di.base_di import BaseDI

__all__ = ["ToolboxDI", "root_causes"]

EXTERNAL_MCP_PREFIX: str = "external_mcp_"

USERS_CONNECTOR_NAME: str = "users"

SANDBOX_TIMEOUT_SECONDS: int = 18000
SANDBOX_MAX_MEMORY_MB: int = 256
SANDBOX_MAX_CONCURRENCY: int = 8


class ToolboxDI(BaseDI):
    async def _invoke_tool_use_case(self) -> InvokeToolUseCase:
        catalog: ToolCatalog = self._tool_catalog
        if not catalog.tools:
            working_directory: WorkingDirectory | None = self._working_directory()
            catalog.add(self._execute_python(catalog.without(ExecutePython.name)))
            catalog.add(
                QueryUsers(await self._sqlite_repository(USERS_CONNECTOR_NAME), SqlHandlerFactory())
            )
            catalog.add(ReadFile(Handler, working_directory))
            catalog.add(WriteFile(Handler, working_directory))
            await self._external_tools_reconciler.reconcile()
        return InvokeToolUseCase(catalog, self._logging)

    @cached_property
    def _tool_catalog(self) -> ToolCatalog:
        return ToolCatalog()

    @cached_property
    def _dependency_health(self) -> DependencyHealth:
        return DependencyHealth()

    @cached_property
    def _external_tools_reconciler(self) -> ReconcileExternalTools:
        return ReconcileExternalTools(
            self._external_sources,
            self._tool_catalog,
            self._dependency_health,
            self._logging,
            describe_error=root_causes,
        )

    @cached_property
    def _external_mcp_connectors(self) -> dict[str, McpConnector]:
        connectors: Mapping[str, McpConnector] = self._configuration.connector[ConnectorType.mcp]
        return {
            name: connector
            for name, connector in connectors.items()
            if name.startswith(EXTERNAL_MCP_PREFIX)
        }

    @cached_property
    def _mcp_operation(self) -> dict[str, McpOperation]:
        return {
            operation.connector.name: operation
            for operation in self._configuration.operation.by_name.values()
            if isinstance(operation, McpOperation)
        }

    @cached_property
    def _external_sources(self) -> list[ExternalSource]:
        operations: dict[str, McpOperation] = self._mcp_operation
        sources: list[ExternalSource] = []
        for name, connector in self._external_mcp_connectors.items():
            short_name: str = name.removeprefix(EXTERNAL_MCP_PREFIX)
            if not connector.base_url.strip():
                self._logging.info(f"External MCP '{short_name}' has no URL, skipping it")
                continue
            operation: McpOperation | None = operations.get(connector.name)
            parameters: Mapping[str, Any] = operation.parameters if operation else {}
            provider = McpToolProvider(
                McpSessionFactory(connector, operation),
                prefix=str(parameters.get("prefix") or short_name),
                allowed=list(parameters.get("tools") or []) or None,
            )
            sources.append(ExternalSource(short_name, provider, refresh_policy(connector)))
        return sources

    def _working_directory(self) -> WorkingDirectory | None:
        directory: Path | None = self._settings.working_directory
        return WorkingDirectory(str(directory)) if directory else None

    def _execute_python(self, data_tools: ToolLookup | Iterable[Tool]) -> ExecutePython:
        working_directory: WorkingDirectory | None = self._working_directory()
        root: str | None = working_directory.root if working_directory else None
        lookup: ToolLookup = (
            data_tools if isinstance(data_tools, ToolLookup) else ToolCatalog(data_tools)
        )

        bridge: SandboxToolBridge | None = None
        if self._settings.sandbox_tool_access:
            bridge = SandboxToolBridge(InvokeToolUseCase(lookup, self._logging))

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
            signatures=(lambda: [python_stub(tool) for tool in lookup.tools]) if bridge else None,
        )

    async def _sqlite_repository(self, connector_name: str) -> AsyncRepository:
        connector: DatabaseConnector = self._configuration.connector.database(connector_name)
        factory: AsyncRepositoryFactory = SqliteRepositoryFactory(SqliteSettingsMapper(connector)())
        self._register_repository(factory)
        return await factory.connect()


def refresh_policy(connector: McpConnector) -> RefreshPolicy:
    return RefreshPolicy(
        interval=connector.refresh.interval,
        retry_delay=connector.refresh.retry_delay,
        max_retry_delay=connector.refresh.max_retry_delay,
    )

from functools import cached_property
from pathlib import Path

from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from agent_toolbox.application.catalog.scoped_tool_catalog import ScopedToolCatalog
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.domain.model.tool_scope import ALL_TOOLS, ToolScope
from agent_toolbox.domain.model.working_directory import WorkingDirectory
from bootstrap.di.auth_di import AuthDI
from bootstrap.di.base_di import BaseDI
from bootstrap.di.external_mcp_di import ExternalMcpDI
from bootstrap.di.internal_tools_di import InternalToolsDI
from bootstrap.di.sandbox_di import SandboxDI
from bootstrap.di.scopes_di import ScopesDI


class ToolboxDI(BaseDI):
    @cached_property
    def _tool_catalog(self) -> ToolCatalog:
        return ToolCatalog()

    @cached_property
    def _working_directory(self) -> WorkingDirectory | None:
        directory: Path | None = self._settings.working_directory
        return WorkingDirectory(str(directory)) if directory else None

    @cached_property
    def _auth(self) -> AuthDI:
        return AuthDI(self._settings.jwt_key, self._settings.jwt_username)

    @cached_property
    def _internal_tools(self) -> InternalToolsDI:
        return InternalToolsDI(
            self._configuration, self._working_directory, self._register_repository
        )

    @cached_property
    def _sandbox(self) -> SandboxDI:
        return SandboxDI(self._logging, self._working_directory, self._settings.sandbox_tool_access)

    @cached_property
    def _external_mcp(self) -> ExternalMcpDI:
        return ExternalMcpDI(self._configuration, self._logging, self._tool_catalog)

    @cached_property
    def _scopes(self) -> ScopesDI:
        return ScopesDI(self._configuration, self._logging, self._external_mcp.waits_for_its_server)

    async def _ready_catalog(self) -> ToolCatalog:
        catalog: ToolCatalog = self._tool_catalog
        if not catalog.tools:
            for tool in await self._internal_tools.tools():
                catalog.add(tool)
            await self._external_mcp.reconciler.reconcile()
        return catalog

    async def _scope_tools(self, scope: ToolScope = ALL_TOOLS) -> ScopedToolCatalog:
        tools = ScopedToolCatalog(await self._ready_catalog(), scope)
        if scope.includes(ExecutePython.name):
            tools = tools.with_own(self._sandbox.execute_python(tools))
        self._scopes.check(tools)
        return tools

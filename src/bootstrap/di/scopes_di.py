from collections.abc import Callable
from functools import cached_property

from pycraftcore.application_configuration import ApplicationConfiguration
from pycraftcore.application_configuration.model import McpConnector, McpOperation
from pycraftcore.logger.port import Logger

from agent_toolbox.application.catalog.scoped_tool_catalog import ScopedToolCatalog
from agent_toolbox.domain.model.tool_scope import ALL_TOOLS, ToolAlias, ToolScope

SELF_CONNECTOR_NAME: str = "self"


class ScopesDI:
    def __init__(
        self,
        configuration: ApplicationConfiguration,
        logger: Logger,
        waits_for_its_server: Callable[[str], bool],
    ) -> None:
        self._configuration = configuration
        self._logger = logger
        self._waits_for_its_server = waits_for_its_server

    @cached_property
    def self_connector(self) -> McpConnector:
        return self._configuration.connector.mcp(SELF_CONNECTOR_NAME)

    @cached_property
    def operations(self) -> tuple[McpOperation, ...]:
        return tuple(
            operation
            for operation in self._configuration.operation.by_name.values()
            if isinstance(operation, McpOperation)
            and operation.connector.name == self.self_connector.name
        )

    @cached_property
    def declared(self) -> tuple[ToolScope, ...]:
        configured: list[ToolScope] = [scope_from(operation) for operation in self.operations]
        names: list[str] = [scope.name for scope in configured]
        duplicated: set[str] = {name for name in names if names.count(name) > 1}
        if duplicated:
            raise ValueError(f"tool scopes declared twice: {', '.join(sorted(duplicated))}")
        return (ALL_TOOLS, *configured)

    def check(self, tools: ScopedToolCatalog) -> None:
        broken: list[str] = []
        for name, problem in tools.unresolved_aliases.items():
            alias: ToolAlias | None = tools.scope.alias(name)
            if alias is not None and self._waits_for_its_server(alias.target):
                self._logger.warning(
                    f"Scope '{tools.scope.name}': {problem}; it is published once its MCP "
                    "server answers"
                )
            else:
                broken.append(problem)
        if broken:
            raise ValueError(f"scope '{tools.scope.name}': {'; '.join(broken)}")


def scope_from(operation: McpOperation) -> ToolScope:
    try:
        aliases: tuple[ToolAlias, ...] = tuple(
            ToolAlias(tool.name, tool.tool, tool.description, tool.arguments)
            for tool in operation.wrapped_tools
        )
        return ToolScope(operation.name, operation.listed_tools, aliases)
    except ValueError as error:
        raise ValueError(
            f"MCP operation '{operation.name}' is not a valid scope: {error}"
        ) from error

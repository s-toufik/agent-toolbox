from collections.abc import Mapping
from functools import cached_property

from pycraftcore.application_configuration import ApplicationConfiguration
from pycraftcore.application_configuration.enum import ConnectorType
from pycraftcore.application_configuration.model import McpConnector, McpOperation
from pycraftcore.logger.port import Logger
from pycraftcore.mcp_sdk import SdkMcpClient

from agent_toolbox.adapter.outbound.mcp.mcp_tool_provider import McpToolProvider
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.application.port.outbound.tool_provider_port import ExternalSource
from agent_toolbox.application.use_case.reconcile_external_tools import ReconcileExternalTools
from agent_toolbox.domain.model.dependency_health import DependencyHealth

EXTERNAL_MCP_PREFIX: str = "external_mcp_"


class ExternalMcpDI:
    def __init__(
        self, configuration: ApplicationConfiguration, logger: Logger, catalog: ToolCatalog
    ) -> None:
        self._configuration = configuration
        self._logger = logger
        self._catalog = catalog

    @cached_property
    def health(self) -> DependencyHealth:
        return DependencyHealth()

    @cached_property
    def reconciler(self) -> ReconcileExternalTools:
        return ReconcileExternalTools(self.sources, self._catalog, self.health, self._logger)

    @cached_property
    def connectors(self) -> dict[str, McpConnector]:
        declared: Mapping[str, McpConnector] = self._configuration.connector[ConnectorType.mcp]
        return {
            name: connector
            for name, connector in declared.items()
            if name.startswith(EXTERNAL_MCP_PREFIX)
        }

    @cached_property
    def operations(self) -> dict[str, McpOperation]:
        names: set[str] = {connector.name for connector in self.connectors.values()}
        return {
            operation.connector.name: operation
            for operation in self._configuration.operation.by_name.values()
            if isinstance(operation, McpOperation) and operation.connector.name in names
        }

    @cached_property
    def prefixes(self) -> dict[str, str]:
        prefixes: dict[str, str] = {}
        for name, connector in self.connectors.items():
            short_name: str = name.removeprefix(EXTERNAL_MCP_PREFIX)
            operation: McpOperation | None = self.operations.get(connector.name)
            prefixes[short_name] = (operation.prefix if operation else None) or short_name
        return prefixes

    @cached_property
    def sources(self) -> list[ExternalSource]:
        sources: list[ExternalSource] = []
        for name, connector in self.connectors.items():
            short_name: str = name.removeprefix(EXTERNAL_MCP_PREFIX)
            if not connector.base_url.strip():
                self._logger.info(f"External MCP '{short_name}' has no URL, skipping it")
                continue
            operation: McpOperation | None = self.operations.get(connector.name)
            if operation is not None and operation.wrapped_tools:
                raise ValueError(
                    f"MCP operation '{operation.name}' wraps tools: wrap them in a scope instead"
                )
            provider = McpToolProvider(
                SdkMcpClient(connector, operation, self._logger),
                prefix=self.prefixes[short_name],
                allowed=(operation.listed_tools if operation else ()) or None,
            )
            sources.append(ExternalSource(short_name, provider, connector.refresh))
        return sources

    def waits_for_its_server(self, tool_name: str) -> bool:
        return any(
            tool_name.startswith(f"{prefix}_") and not self.health.is_up(source)
            for source, prefix in self.prefixes.items()
        )

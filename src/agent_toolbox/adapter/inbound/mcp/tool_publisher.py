from mcp.server.mcpserver import MCPServer

from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from agent_toolbox.application.port.outbound.tool_lookup_port import ToolLookup
from agent_toolbox.application.port.outbound.tool_publisher_port import CatalogChange


class McpToolPublisher:
    def __init__(
        self,
        server: MCPServer,
        binder: ToolBinder,
        catalog: ToolLookup,
        refreshed: tuple[str, ...] = (),
    ) -> None:
        self._server = server
        self._binder = binder
        self._catalog = catalog
        self._refreshed = refreshed

    def publish(self, change: CatalogChange) -> None:
        for name in change.removed:
            self._binder.unbind(self._server, name)
        for tool in change.added:
            self._binder.bind_one(self._server, tool)
        for name in self._refreshed:
            tool = self._catalog.get(name)
            if tool is not None:
                self._binder.unbind(self._server, name)
                self._binder.bind_one(self._server, tool)

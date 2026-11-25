from pycraftcore.mcp import ToolServer

from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from agent_toolbox.application.port.outbound.tool_lookup_port import ToolLookup
from agent_toolbox.application.port.outbound.tool_publisher_port import CatalogChange
from agent_toolbox.domain.model.tool_scope import ALL_TOOLS, ToolScope


class McpToolPublisher:
    def __init__(
        self,
        server: ToolServer,
        binder: ToolBinder,
        catalog: ToolLookup,
        refreshed: tuple[str, ...] = (),
        scope: ToolScope = ALL_TOOLS,
    ) -> None:
        self._scope = scope
        self._server = server
        self._binder = binder
        self._catalog = catalog
        self._refreshed = refreshed

    def publish(self, change: CatalogChange) -> None:
        for name in change.removed:
            if self._scope.includes(name):
                self._binder.unbind(self._server, name)
        for tool in change.added:
            if self._scope.includes(tool.name):
                self._binder.bind_one(self._server, tool)
        changed: set[str] = {*change.removed, *(tool.name for tool in change.added)}
        for alias in self._scope.aliases:
            if alias.target in changed:
                self._rebind(alias.name)
        for name in self._refreshed:
            self._rebind(name)

    def _rebind(self, name: str) -> None:
        self._binder.unbind(self._server, name)
        tool = self._catalog.get(name)
        if tool is not None:
            self._binder.bind_one(self._server, tool)

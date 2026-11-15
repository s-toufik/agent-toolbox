from collections.abc import Iterable

from agent_toolbox.application.port.outbound.tool_lookup_port import ToolLookup
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.model.tool_scope import ToolScope


class ScopedToolCatalog:
    def __init__(self, catalog: ToolLookup, scope: ToolScope, own: Iterable[Tool] = ()) -> None:
        self._catalog = catalog
        self._scope = scope
        self._own: dict[str, Tool] = {tool.name: tool for tool in own}

    @property
    def scope(self) -> ToolScope:
        return self._scope

    @property
    def tools(self) -> tuple[Tool, ...]:
        shared = tuple(
            tool
            for tool in self._catalog.tools
            if self._scope.includes(tool.name) and tool.name not in self._own
        )
        return (*self._own.values(), *shared)

    def get(self, name: str) -> Tool | None:
        if name in self._own:
            return self._own[name]
        return self._catalog.get(name) if self._scope.includes(name) else None

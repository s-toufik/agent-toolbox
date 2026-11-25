from collections.abc import Iterable
from dataclasses import dataclass

from agent_toolbox.application.catalog.aliased_tool import AliasedTool
from agent_toolbox.application.port.outbound.tool_lookup_port import ToolLookup
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.model.tool_scope import ToolAlias, ToolScope


@dataclass(frozen=True, slots=True)
class _Resolution:
    target: Tool | None
    tool: AliasedTool | None = None
    problem: str | None = None


class ScopedToolCatalog:
    def __init__(self, catalog: ToolLookup, scope: ToolScope, own: Iterable[Tool] = ()) -> None:
        self._catalog = catalog
        self._scope = scope
        self._own: dict[str, Tool] = {tool.name: tool for tool in own}
        self._resolutions: dict[str, _Resolution] = {}

    @property
    def scope(self) -> ToolScope:
        return self._scope

    def with_own(self, *tools: Tool) -> ScopedToolCatalog:
        scoped = ScopedToolCatalog(self._catalog, self._scope, own=(*self._own.values(), *tools))
        scoped._resolutions = self._resolutions
        return scoped

    @property
    def tools(self) -> tuple[Tool, ...]:
        aliased: tuple[Tool, ...] = tuple(
            resolution.tool
            for alias in self._scope.aliases
            if (resolution := self._resolve(alias)).tool is not None
        )
        shared: tuple[Tool, ...] = tuple(
            tool
            for tool in self._catalog.tools
            if self._scope.includes(tool.name) and tool.name not in self._own
        )
        return (*self._own.values(), *aliased, *shared)

    @property
    def unresolved_aliases(self) -> dict[str, str]:
        return {
            alias.name: resolution.problem
            for alias in self._scope.aliases
            if (resolution := self._resolve(alias)).problem is not None
        }

    def get(self, name: str) -> Tool | None:
        if name in self._own:
            return self._own[name]
        alias: ToolAlias | None = self._scope.alias(name)
        if alias is not None:
            return self._resolve(alias).tool
        return self._catalog.get(name) if self._scope.includes(name) else None

    def _resolve(self, alias: ToolAlias) -> _Resolution:
        target: Tool | None = self._catalog.get(alias.target)
        cached: _Resolution | None = self._resolutions.get(alias.name)
        if cached is not None and cached.target is target:
            return cached
        resolution: _Resolution = _build(alias, target)
        self._resolutions[alias.name] = resolution
        return resolution


def _build(alias: ToolAlias, target: Tool | None) -> _Resolution:
    if target is None:
        return _Resolution(
            None, problem=f"alias '{alias.name}': its tool '{alias.target}' is not in the catalog"
        )
    try:
        return _Resolution(target, tool=AliasedTool(alias, target))
    except ValueError as error:
        return _Resolution(target, problem=str(error))

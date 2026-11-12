import json
from collections.abc import Iterable
from dataclasses import dataclass

from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.application.port.outbound.tool_publisher_port import CatalogChange


@dataclass(frozen=True)
class _Entry:
    source: str | None
    tool: Tool


class ToolCatalog:
    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._entries: dict[str, _Entry] = {}
        for tool in tools:
            self.add(tool)

    @property
    def tools(self) -> tuple[Tool, ...]:
        return tuple(entry.tool for entry in self._entries.values())

    def get(self, name: str) -> Tool | None:
        entry: _Entry | None = self._entries.get(name)
        return entry.tool if entry else None

    def add(self, tool: Tool) -> None:
        if tool.name in self._entries:
            raise ValueError(f"Duplicate tool name: '{tool.name}'")
        self._entries[tool.name] = _Entry(None, tool)

    def without(self, *names: str) -> ToolCatalogView:
        return ToolCatalogView(self, frozenset(names))

    def replace(self, source: str, tools: Iterable[Tool]) -> CatalogChange:
        current: dict[str, Tool] = {
            name: entry.tool for name, entry in self._entries.items() if entry.source == source
        }
        wanted: dict[str, Tool] = {}
        conflicts: list[str] = []
        for tool in tools:
            owner: _Entry | None = self._entries.get(tool.name)
            if (owner is not None and owner.source != source) or tool.name in wanted:
                conflicts.append(tool.name)
                continue
            wanted[tool.name] = tool

        removed: list[str] = [
            name
            for name, tool in current.items()
            if name not in wanted or _fingerprint(tool) != _fingerprint(wanted[name])
        ]
        added: list[Tool] = [
            tool for name, tool in wanted.items() if name not in current or name in removed
        ]

        for name in removed:
            del self._entries[name]
        for name, tool in wanted.items():
            self._entries[name] = _Entry(source, tool)

        return CatalogChange(tuple(added), tuple(removed), tuple(conflicts))


class ToolCatalogView:
    def __init__(self, catalog: ToolCatalog, hidden: frozenset[str]) -> None:
        self._catalog = catalog
        self._hidden = hidden

    @property
    def tools(self) -> tuple[Tool, ...]:
        return tuple(tool for tool in self._catalog.tools if tool.name not in self._hidden)

    def get(self, name: str) -> Tool | None:
        return None if name in self._hidden else self._catalog.get(name)


def _fingerprint(tool: Tool) -> str:
    return json.dumps(
        [tool.description, tool.input_model.model_json_schema()], sort_keys=True, default=str
    )

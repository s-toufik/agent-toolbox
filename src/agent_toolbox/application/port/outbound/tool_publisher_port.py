from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from agent_toolbox.application.port.outbound.tool_port import Tool


@dataclass(frozen=True)
class CatalogChange:
    added: tuple[Tool, ...] = ()
    removed: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = field(default=(), compare=False)

    def __bool__(self) -> bool:
        return bool(self.added or self.removed)


@runtime_checkable
class ToolPublisher(Protocol):
    def publish(self, change: CatalogChange) -> None: ...

from typing import Protocol, runtime_checkable

from agent_toolbox.application.port.outbound.tool_port import Tool


@runtime_checkable
class ToolLookup(Protocol):
    @property
    def tools(self) -> tuple[Tool, ...]: ...

    def get(self, name: str) -> Tool | None: ...

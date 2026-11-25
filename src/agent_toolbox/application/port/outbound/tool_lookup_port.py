from typing import Protocol

from agent_toolbox.application.port.outbound.tool_port import Tool


class ToolLookup(Protocol):
    @property
    def tools(self) -> tuple[Tool, ...]: ...

    def get(self, name: str) -> Tool | None: ...

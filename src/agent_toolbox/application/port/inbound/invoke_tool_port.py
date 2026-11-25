from collections.abc import Mapping
from typing import Any, Protocol

from agent_toolbox.application.port.outbound.tool_port import Tool


class InvokeToolPort(Protocol):
    @property
    def tools(self) -> tuple[Tool, ...]: ...

    async def invoke(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]: ...

from dataclasses import dataclass, field
from typing import Protocol

from pycraftcore.application_configuration.model import McpRefresh

from agent_toolbox.application.port.outbound.tool_port import Tool


class ToolProvider(Protocol):
    async def tools(self) -> list[Tool]: ...


@dataclass(frozen=True)
class ExternalSource:
    name: str
    provider: ToolProvider
    policy: McpRefresh = field(default_factory=McpRefresh)

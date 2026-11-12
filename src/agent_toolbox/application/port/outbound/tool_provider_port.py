from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.model.refresh_policy import RefreshPolicy


@runtime_checkable
class ToolProvider(Protocol):
    async def tools(self) -> list[Tool]: ...


@dataclass(frozen=True)
class ExternalSource:
    name: str
    provider: ToolProvider
    policy: RefreshPolicy = field(default_factory=RefreshPolicy)

from dataclasses import dataclass

from agent_toolbox.domain.model.tool_invocation import ToolInvocation


@dataclass(frozen=True, slots=True)
class ToolOutcome[T]:
    invocation_id: str
    tool_name: str
    output: T | None
    error: str | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None

    @classmethod
    def success(cls, invocation: ToolInvocation, output: T) -> ToolOutcome[T]:
        return cls(invocation.id, invocation.name, output=output)

    @classmethod
    def failure(cls, invocation: ToolInvocation, error: str) -> ToolOutcome[T]:
        return cls(invocation.id, invocation.name, output=None, error=error)

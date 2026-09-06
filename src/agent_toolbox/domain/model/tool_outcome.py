from dataclasses import dataclass

from agent_toolbox.domain.model.tool_invocation import ToolInvocation


@dataclass(frozen=True, slots=True)
class ToolOutcome:
    invocation_id: str
    tool_name: str
    output: str
    error: str | None = None

    @property
    def failed(self) -> bool:
        return bool(self.error)

    @property
    def content(self) -> str:
        if not self.failed:
            return self.output
        if self.output:
            return f"{self.output}\nError: {self.error}"
        return f"Error: {self.error}"

    @classmethod
    def success(cls, invocation: ToolInvocation, output: str) -> ToolOutcome:
        return cls(invocation_id=invocation.id, tool_name=invocation.name, output=output)

    @classmethod
    def failure(cls, invocation: ToolInvocation, error: str, output: str = "") -> ToolOutcome:
        return cls(
            invocation_id=invocation.id,
            tool_name=invocation.name,
            output=output,
            error=error,
        )

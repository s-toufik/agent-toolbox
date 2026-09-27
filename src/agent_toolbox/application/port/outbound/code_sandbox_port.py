from typing import Protocol, runtime_checkable

from agent_toolbox.domain.model.sandbox_run import SandboxRun


@runtime_checkable
class CodeSandboxPort(Protocol):
    async def run(self, code: str) -> SandboxRun:
        ...

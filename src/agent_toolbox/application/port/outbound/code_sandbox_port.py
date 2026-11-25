from typing import Protocol

from agent_toolbox.domain.model.sandbox_run import SandboxRun


class CodeSandboxPort(Protocol):
    async def run(self, code: str) -> SandboxRun: ...

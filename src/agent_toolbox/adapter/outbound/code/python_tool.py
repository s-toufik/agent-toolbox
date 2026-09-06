import asyncio

from pycraftcore.runtime import Code, CodeFactory
from pycraftcore.runtime.configuration import CodeStdout

from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome
from agent_toolbox.domain.model.tool_specification import ToolSpecification


class PythonTool:
    def __init__(
        self,
        code_factory: CodeFactory,
        specification: ToolSpecification,
        semaphore: asyncio.Semaphore,
    ) -> None:
        self._code_factory = code_factory
        self._specification = specification
        self._semaphore = semaphore

    @property
    def specification(self) -> ToolSpecification:
        return self._specification

    async def invoke(self, invocation: ToolInvocation) -> ToolOutcome:
        code: str = invocation.argument("code", "") or ""

        if not code.strip():
            return ToolOutcome.failure(invocation, "No code provided.")

        executor: Code = self._code_factory(code=code, code_template=None)

        async with self._semaphore:
            result: CodeStdout = await executor.execute()

        if result.stderr:
            return ToolOutcome.failure(invocation, result.stderr, output=result.stdout)
        return ToolOutcome.success(invocation, result.stdout)

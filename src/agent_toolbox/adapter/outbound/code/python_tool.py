from collections.abc import Callable, Iterable
from dataclasses import replace

from agent_toolbox.adapter.outbound.code.model.python_execution_input import ExecutePythonInput
from agent_toolbox.adapter.outbound.code.model.python_execution_output import ExecutePythonOutput
from agent_toolbox.adapter.outbound.code.python_tool_description import PythonToolDescription
from agent_toolbox.application.port.outbound.code_sandbox_port import CodeSandboxPort
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.sandbox_run import SandboxRun


class ExecutePython(Tool[ExecutePythonInput, ExecutePythonOutput]):
    name = "python_executor"
    input_model = ExecutePythonInput
    output_model = ExecutePythonOutput

    def __init__(
        self,
        sandbox: CodeSandboxPort,
        allowed_modules: Iterable[str],
        timeout_seconds: int,
        working_directory: str | None = None,
        callable_tools: Callable[[], Iterable[str]] = tuple,
    ) -> None:
        self._sandbox = sandbox
        self._described = PythonToolDescription(
            tuple(sorted(allowed_modules)), timeout_seconds, working_directory
        )
        self._callable_tools = callable_tools

    @property
    def description(self) -> str:
        return replace(self._described, callable_tools=tuple(self._callable_tools())).render()

    @description.setter
    def description(self, _: str) -> None:
        raise AttributeError("python_executor's description is built from the tools it can call")

    async def run(self, arguments: ExecutePythonInput) -> ExecutePythonOutput:
        if not arguments.code.strip():
            raise ToolFailure("No code provided.")

        run: SandboxRun = await self._sandbox.run(arguments.code)
        return ExecutePythonOutput(result_type=run.type_name, result=run.value, stdout=run.printed)

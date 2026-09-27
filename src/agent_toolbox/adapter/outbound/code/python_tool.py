from collections.abc import Iterable

from agent_toolbox.adapter.outbound.code.model.python_execution_input import ExecutePythonInput
from agent_toolbox.adapter.outbound.code.model.python_execution_output import ExecutePythonOutput
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
        tool_signatures: Iterable[str] = (),
    ) -> None:
        self._sandbox = sandbox
        self.description = _description(
            sorted(allowed_modules), timeout_seconds, working_directory, tuple(tool_signatures)
        )

    async def run(self, arguments: ExecutePythonInput) -> ExecutePythonOutput:
        if not arguments.code.strip():
            raise ToolFailure("No code provided.")

        run: SandboxRun = await self._sandbox.run(arguments.code)
        return ExecutePythonOutput(result_type=run.type_name, result=run.value, stdout=run.printed)


def _description(
    allowed_modules: list[str],
    timeout_seconds: int,
    working_directory: str | None,
    tool_signatures: tuple[str, ...],
) -> str:
    text = (
        "Execute Python code for data analysis or computation. "
        f"Allowed modules: {', '.join(allowed_modules)}. "
        "Assign your final value to a variable named 'result'; "
        "if returning a result is not relevant, set result='no return'. "
        f"Hard timeout: {timeout_seconds} seconds."
    )

    if working_directory:
        text += (
            " This tool is where heavy file analysis and generation belongs; the file_reader "
            "and file_writer tools are only for quick inspection and small writes. A shared "
            "working directory is the current directory of your code and is exposed to it as "
            "the 'WORKING_DIRECTORY' variable: read every input file from it and write every "
            "output there, using relative paths or the WORKING_DIRECTORY variable. File access "
            "outside the working directory is denied. The file tools resolve relative paths "
            "against the working directory too, so a path names the same file in your code and "
            f"in a tool call. Working directory: {working_directory}."
        )

    if tool_signatures:
        text += (
            "\n\nInside your code these tools are available as functions. Call them with keyword "
            "arguments; each returns exactly what calling the tool directly returns, as plain "
            "dicts and lists. A failing call raises ToolError with the tool's error message. "
            "Arguments must be plain JSON values (dict, list, str, int, float, bool, None): "
            "convert a DataFrame with json.loads(df.to_json(orient='records', "
            "date_format='iso')) and a numpy number with .item().\n\n" + "\n".join(tool_signatures)
        )

    return text

import pytest

from agent_toolbox.adapter.outbound.code.model.python_execution_input import ExecutePythonInput
from agent_toolbox.adapter.outbound.code.model.python_execution_output import ExecutePythonOutput
from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from agent_toolbox.adapter.outbound.code.python_tool_description import (
    LEAD_ALONE,
    LEAD_WITH_TOOLS,
)
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.sandbox_run import SandboxRun
from tests.agent_toolbox.stubs import StubSandbox


def _tool(sandbox: StubSandbox, **options) -> ExecutePython:
    return ExecutePython(sandbox, allowed_modules=("math", "json"), timeout_seconds=30, **options)


async def test_returns_the_sandbox_result_and_what_the_code_printed() -> None:
    sandbox = StubSandbox(SandboxRun(type_name="dict", value={"a": 1}, printed="hi"))

    output = await _tool(sandbox).run(ExecutePythonInput(code="print('hi'); result = {'a': 1}"))

    assert output == ExecutePythonOutput(result_type="dict", result={"a": 1}, stdout="hi")


async def test_empty_code_is_rejected_without_running_anything() -> None:
    sandbox = StubSandbox()

    with pytest.raises(ToolFailure, match="No code provided."):
        await _tool(sandbox).run(ExecutePythonInput(code="   "))

    assert sandbox.codes == []


async def test_sandbox_errors_propagate_unchanged() -> None:
    with pytest.raises(ToolFailure, match="NameError: name 'x' is not defined"):
        await _tool(StubSandbox(error="NameError: name 'x' is not defined")).run(
            ExecutePythonInput(code="result = x")
        )


def test_description_lists_modules_and_timeout_only_by_default() -> None:
    description = _tool(StubSandbox()).description

    assert description.startswith(LEAD_ALONE)
    assert "Modules: json, math." in description
    assert "Timeout: 30 seconds." in description
    assert "WORKING_DIRECTORY" not in description
    assert "ToolError" not in description


def test_description_names_the_tools_it_can_call_as_they_are_now() -> None:
    names: list[str] = ["echo"]
    tool = _tool(StubSandbox(), working_directory="/work", callable_tools=lambda: names)

    before = tool.description
    names.append("grafana_search")
    after = tool.description

    assert before.startswith(LEAD_WITH_TOOLS)
    assert "Tools callable in code: echo." in before
    assert "Tools callable in code: echo, grafana_search." in after
    assert "- Files: /work is the code's current directory" in after

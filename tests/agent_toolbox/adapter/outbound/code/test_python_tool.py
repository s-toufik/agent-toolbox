import pytest

from agent_toolbox.adapter.outbound.code.model.python_execution_input import ExecutePythonInput
from agent_toolbox.adapter.outbound.code.model.python_execution_output import ExecutePythonOutput
from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
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

    assert "Allowed modules: json, math." in description
    assert "Hard timeout: 30 seconds." in description
    assert "VAULT" not in description
    assert "ToolError" not in description


def test_description_mentions_the_vault_and_callable_tools_when_configured() -> None:
    description = _tool(
        StubSandbox(), vault_path="/vault", tool_signatures=["echo(*, text: str) -> {echoed: str}"]
    ).description

    assert "Vault location: /vault." in description
    assert "echo(*, text: str) -> {echoed: str}" in description
    assert "raises ToolError" in description
    assert "Arguments must be plain JSON values" in description
    assert "The file tools resolve relative paths against the vault too" in description

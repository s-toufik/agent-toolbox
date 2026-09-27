import asyncio
import json

import pytest
from pycraftcore.runtime.schema import CodeStdout

from agent_toolbox.adapter.outbound.sandbox.python_sandbox import PythonSandbox
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.sandbox_run import SandboxRun


class StubCode:
    def __init__(self, stdout: str, stderr: str) -> None:
        self._output = CodeStdout(stdout=stdout, stderr=stderr)

    async def execute(self) -> CodeStdout:
        return self._output


def _sandbox(stdout: str = "", stderr: str = "") -> PythonSandbox:
    def factory(code, code_template=None, host_bridge=None):
        return StubCode(stdout, stderr)

    return PythonSandbox(factory, asyncio.Semaphore(1))


def _envelope(value, type_name: str) -> str:
    return json.dumps({"__type__": type_name, "result": value})


async def test_parses_the_result_and_keeps_printed_output() -> None:
    run = await _sandbox(stdout="hello\n" + _envelope([1, 2], "list")).run("...")

    assert run == SandboxRun(type_name="list", value=[1, 2], printed="hello")


async def test_warnings_on_stderr_do_not_fail_a_run_that_produced_a_result() -> None:
    run = await _sandbox(stdout=_envelope(1, "int"), stderr="FutureWarning: ...").run("...")

    assert run.value == 1


async def test_a_run_without_a_result_fails_with_stderr_only() -> None:
    sandbox = _sandbox(stdout="partial output", stderr="NameError: name 'x' is not defined")

    with pytest.raises(ToolFailure, match="^NameError: name 'x' is not defined$"):
        await sandbox.run("print('partial output'); x")


async def test_real_sandbox_run_without_a_bridge() -> None:
    from pycraftcore.runtime.adapter import PythonSafeCodeFactory

    sandbox = PythonSandbox(PythonSafeCodeFactory(), asyncio.Semaphore(1))

    run = await sandbox.run("print('hi')\nresult = {'total': sum([1, 2, 3])}")

    assert run == SandboxRun(type_name="dict", value={"total": 6}, printed="hi")

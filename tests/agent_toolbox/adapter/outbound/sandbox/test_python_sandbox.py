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


async def test_a_failed_run_reports_what_it_printed_then_the_error() -> None:
    sandbox = _sandbox(stdout="partial output", stderr="NameError: name 'x' is not defined")

    with pytest.raises(ToolFailure) as failure:
        await sandbox.run("print('partial output'); x")

    assert str(failure.value) == (
        "Printed before the error:\npartial output\n\nNameError: name 'x' is not defined"
    )


async def test_a_failed_run_that_printed_nothing_reports_only_the_error() -> None:
    sandbox = _sandbox(stderr="NameError: name 'x' is not defined")

    with pytest.raises(ToolFailure, match="^NameError: name 'x' is not defined$"):
        await sandbox.run("x")


async def test_a_run_with_no_output_at_all_says_so() -> None:
    with pytest.raises(ToolFailure, match="^The sandbox returned no result.$"):
        await _sandbox().run("...")


async def test_real_sandbox_run_without_a_bridge() -> None:
    from pycraftcore.runtime.adapter import PythonSafeCodeFactory

    sandbox = PythonSandbox(PythonSafeCodeFactory(), asyncio.Semaphore(1))

    run = await sandbox.run("print('hi')\nresult = {'total': sum([1, 2, 3])}")

    assert run == SandboxRun(type_name="dict", value={"total": 6}, printed="hi")


async def test_real_sandbox_failure_keeps_the_printed_output_and_the_error() -> None:
    from pycraftcore.runtime.adapter import PythonSafeCodeFactory

    sandbox = PythonSandbox(PythonSafeCodeFactory(), asyncio.Semaphore(1))

    with pytest.raises(ToolFailure) as failure:
        await sandbox.run("print('loaded 120 rows')\nrows = [1, 2]\nresult = rows[5]\n")

    assert str(failure.value).startswith("Printed before the error:\nloaded 120 rows\n\n")
    assert str(failure.value).endswith("IndexError: list index out of range")

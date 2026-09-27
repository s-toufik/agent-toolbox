import pytest

from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.exception.unknown_tool_exception import UnknownToolException
from tests.agent_toolbox.stubs import Echo


async def test_returns_the_output_model_as_json_ready_data(logger) -> None:
    use_case = InvokeToolUseCase([Echo()], logger)

    output = await use_case.invoke("echo", {"text": "ab", "times": 2}, "call_1")

    assert output == {"echoed": "abab"}
    assert logger.messages("info") == ["[call_1] tool 'echo' invoked"]


async def test_none_arguments_fall_back_to_the_model_defaults(logger) -> None:
    use_case = InvokeToolUseCase([Echo()], logger)

    assert await use_case.invoke("echo", {"text": "a", "times": None}, "1") == {"echoed": "a"}


async def test_unknown_tool_is_a_tool_failure(logger) -> None:
    use_case = InvokeToolUseCase([Echo()], logger)

    with pytest.raises(UnknownToolException, match="Unknown tool: 'nope'."):
        await use_case.invoke("nope", {}, "1")


async def test_invalid_arguments_name_every_problem(logger) -> None:
    use_case = InvokeToolUseCase([Echo()], logger)

    with pytest.raises(ToolFailure) as failure:
        await use_case.invoke("echo", {"times": "many"}, "1")

    assert str(failure.value) == (
        "Invalid arguments for 'echo': text: Field required; "
        "times: Input should be a valid integer, unable to parse string as an integer"
    )


async def test_expected_failures_pass_through_and_are_logged_as_warnings(logger) -> None:
    use_case = InvokeToolUseCase([Echo(error=ToolFailure("File not found."))], logger)

    with pytest.raises(ToolFailure, match="^File not found.$"):
        await use_case.invoke("echo", {"text": "a"}, "1")

    assert logger.messages("warning") == ["[1] tool 'echo': File not found."]


async def test_crashes_become_tool_failures_and_are_logged_with_a_traceback(logger) -> None:
    use_case = InvokeToolUseCase([Echo(error=RuntimeError("boom"))], logger)

    with pytest.raises(ToolFailure, match="^Tool execution failed: boom$"):
        await use_case.invoke("echo", {"text": "a"}, "1")

    [error] = logger.messages("error")
    assert "Traceback" in error and "RuntimeError: boom" in error


def test_exposes_its_tools(logger) -> None:
    echo = Echo()

    assert InvokeToolUseCase([echo], logger).tools == (echo,)

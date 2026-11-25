import pytest
from pycraftcore.mcp import ToolCallError

from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from tests.agent_toolbox.stubs import Echo, EchoInput, EchoOutput, RecordingToolServer


def _server(logger, tool: Echo) -> RecordingToolServer:
    server = RecordingToolServer()
    ToolBinder(InvokeToolUseCase(ToolCatalog([tool]), logger)).bind(server)
    return server


def test_bind_returns_the_bound_tool_names(logger) -> None:
    binder = ToolBinder(InvokeToolUseCase(ToolCatalog([Echo()]), logger))

    assert binder.bind(RecordingToolServer()) == ["echo"]


def test_the_served_tool_carries_the_tool_models_and_described_text(logger) -> None:
    served = _server(logger, Echo()).tools["echo"]

    assert served.name == "echo"
    assert served.description == "Repeat text.\n\nReturns: {echoed: str}"
    assert served.input_model is EchoInput
    assert served.output_model is EchoOutput


async def test_a_call_returns_the_output_model_without_a_wrapper(logger) -> None:
    result = await _server(logger, Echo()).call("echo", {"text": "ab", "times": 2})

    assert result == {"echoed": "abab"}


async def test_tool_failures_become_tool_call_errors_with_their_message(logger) -> None:
    server = _server(logger, Echo(error=ToolFailure("File not found.")))

    with pytest.raises(ToolCallError, match="^File not found.$"):
        await server.call("echo", {"text": "a"})


def test_unbind_removes_the_tool(logger) -> None:
    server = _server(logger, Echo())

    ToolBinder.unbind(server, "echo")

    assert server.tools == {}

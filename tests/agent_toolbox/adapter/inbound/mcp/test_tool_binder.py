import pytest
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from tests.agent_toolbox.stubs import Echo, EchoInput, EchoOutput


def _server(logger, tool: Echo) -> MCPServer:
    server = MCPServer(name="test")
    ToolBinder(InvokeToolUseCase([tool], logger)).bind(server)
    return server


def test_bind_returns_the_bound_tool_names(logger) -> None:
    binder = ToolBinder(InvokeToolUseCase([Echo()], logger))

    assert binder.bind(MCPServer(name="test")) == ["echo"]


async def test_schemas_and_description_come_from_the_tool_models(logger) -> None:
    [listed] = await _server(logger, Echo()).list_tools()

    assert listed.name == "echo"
    assert listed.description == "Repeat text.\n\nReturns: {echoed: str}"
    assert listed.input_schema["properties"].keys() == EchoInput.model_fields.keys()
    assert listed.input_schema["required"] == ["text"]
    assert listed.output_schema == EchoOutput.model_json_schema()


async def test_structured_content_is_the_output_model_without_a_wrapper(logger) -> None:
    result = await _server(logger, Echo()).call_tool("echo", {"text": "ab", "times": 2})

    assert result.structured_content == {"echoed": "abab"}
    assert not result.is_error


async def test_tool_failures_keep_their_message(logger) -> None:
    server = _server(logger, Echo(error=ToolFailure("File not found.")))

    with pytest.raises(ToolError, match="^Error executing tool echo: File not found.$"):
        await server.call_tool("echo", {"text": "a"})

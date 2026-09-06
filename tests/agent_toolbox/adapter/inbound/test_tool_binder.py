import pytest
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from agent_toolbox.adapter.outbound.registry.in_memory_tool_registry import InMemoryToolRegistry
from agent_toolbox.application.use_case.execute_tool_usecase import ExecuteToolUseCase
from agent_toolbox.domain.enum.parameter_type import ParameterType
from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome
from agent_toolbox.domain.model.tool_specification import ToolParameter, ToolSpecification

SPECIFICATION = ToolSpecification(
    name="run_sql",
    description="Execute a read-only SQL query.",
    parameters=(
        ToolParameter(
            name="query",
            type=ParameterType.STRING,
            description="SQL query to execute.",
            required=True,
        ),
        ToolParameter(
            name="dialect",
            type=ParameterType.STRING,
            description="sqlglot dialect.",
            required=False,
        ),
    ),
)


class StubTool:
    def __init__(self) -> None:
        self.seen: list[ToolInvocation] = []

    @property
    def specification(self) -> ToolSpecification:
        return SPECIFICATION

    async def invoke(self, invocation: ToolInvocation) -> ToolOutcome:
        self.seen.append(invocation)
        return ToolOutcome.success(invocation, "[{'n': 1}]")


class FailingTool:
    @property
    def specification(self) -> ToolSpecification:
        return ToolSpecification(name="always_fails", description="Fails.")

    async def invoke(self, invocation: ToolInvocation) -> ToolOutcome:
        return ToolOutcome.failure(invocation, "no")


@pytest.fixture
def tool() -> StubTool:
    return StubTool()


@pytest.fixture
def server(tool: StubTool, logger) -> MCPServer:
    registry = InMemoryToolRegistry([tool, FailingTool()])
    binder = ToolBinder(ExecuteToolUseCase(registry, logger), registry)
    server = MCPServer(name="test-toolbox")
    binder.bind(server)
    return server


async def test_specification_drives_the_advertised_schema(server: MCPServer) -> None:
    tools = {tool.name: tool for tool in await server.list_tools()}

    assert "run_sql" in tools
    schema = tools["run_sql"].input_schema
    assert schema["required"] == ["query"]
    assert schema["properties"]["query"]["type"] == "string"
    assert schema["properties"]["query"]["description"] == "SQL query to execute."
    assert "dialect" in schema["properties"]


async def test_arguments_reach_the_tool(server: MCPServer, tool: StubTool) -> None:
    await server.call_tool("run_sql", {"query": "select 1", "dialect": "sqlite"})

    assert tool.seen[0].arguments == {"query": "select 1", "dialect": "sqlite"}


async def test_unset_optional_argument_is_dropped(server: MCPServer, tool: StubTool) -> None:
    await server.call_tool("run_sql", {"query": "select 1"})

    assert tool.seen[0].arguments == {"query": "select 1"}


async def test_a_pure_failure_carries_its_message_to_the_client(server: MCPServer) -> None:
    # ToolError is what the SDK turns into an is_error result while keeping the
    # message; a bare exception would be replaced by a generic string.
    with pytest.raises(ToolError, match="no"):
        await server.call_tool("always_fails", {})

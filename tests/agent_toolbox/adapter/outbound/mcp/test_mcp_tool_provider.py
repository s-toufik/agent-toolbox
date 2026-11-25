from typing import Any

import pytest
from pycraftcore.mcp import CallResult, McpUnavailableException, RemoteTool
from pydantic import ValidationError

from agent_toolbox.adapter.outbound.mcp.mcp_backed_tool import McpBackedTool
from agent_toolbox.adapter.outbound.mcp.mcp_tool_provider import McpToolProvider, published_name
from agent_toolbox.domain.exception.tool_failure import ToolFailure

LIST_DATABASES = RemoteTool(
    name="list-databases",
    description="List every database.",
    input_schema={"type": "object", "properties": {}},
)
FIND = RemoteTool(
    name="find",
    description="Find documents.",
    input_schema={
        "type": "object",
        "properties": {
            "database": {"type": "string", "description": "Database name"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["database"],
    },
)


class FakeClient:
    def __init__(
        self,
        tools: list[RemoteTool],
        result: CallResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._tools = tools
        self._result = result
        self._error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_tools(self) -> list[RemoteTool]:
        return self._tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallResult:
        self.calls.append((name, arguments))
        if self._error:
            raise self._error
        assert self._result is not None
        return self._result


def test_published_names_are_prefixed_python_identifiers() -> None:
    assert published_name("mongodb", "list-databases") == "mongodb_list_databases"
    assert published_name("grafana", "search_dashboards") == "grafana_search_dashboards"
    assert published_name("", "collection.schema") == "collection_schema"


async def test_tools_are_published_under_the_prefix_and_keep_their_remote_name() -> None:
    tools = await McpToolProvider(FakeClient([LIST_DATABASES, FIND]), prefix="mongodb").tools()

    assert [tool.name for tool in tools] == ["mongodb_list_databases", "mongodb_find"]
    assert [tool.remote_name for tool in tools if isinstance(tool, McpBackedTool)] == [
        "list-databases",
        "find",
    ]
    found = tools[1].input_model(database="kitchen")
    assert (found.database, found.limit) == ("kitchen", 10)


async def test_the_allowlist_keeps_only_the_named_remote_tools() -> None:
    client = FakeClient([LIST_DATABASES, FIND])

    tools = await McpToolProvider(client, prefix="mongodb", allowed=["find"]).tools()

    assert [tool.name for tool in tools] == ["mongodb_find"]


async def test_two_servers_with_the_same_tool_name_no_longer_collide() -> None:
    mongo = await McpToolProvider(FakeClient([FIND]), prefix="mongodb").tools()
    postgres = await McpToolProvider(FakeClient([FIND]), prefix="postgres").tools()

    assert {tool.name for tool in mongo + postgres} == {"mongodb_find", "postgres_find"}


async def test_a_call_uses_the_remote_name_and_returns_the_text() -> None:
    client = FakeClient([LIST_DATABASES], CallResult(content=("admin, agent_runtime",)))
    [tool] = await McpToolProvider(client, prefix="mongodb").tools()

    output = await tool.run(tool.input_model())

    assert client.calls == [("list-databases", {})]
    assert output.model_dump() == {"result": "admin, agent_runtime"}


async def test_structured_content_is_the_output() -> None:
    remote = RemoteTool(
        name="count",
        input_schema={"type": "object", "properties": {}},
        output_schema={
            "type": "object",
            "properties": {"total": {"type": "integer"}},
            "required": ["total"],
        },
    )
    client = FakeClient([remote], CallResult(content=('{"total": 3}',), structured={"total": 3}))
    [tool] = await McpToolProvider(client).tools()

    output = await tool.run(tool.input_model())

    assert output.model_dump() == {"total": 3}


async def test_a_remote_call_sends_nested_arguments_unchanged_and_refuses_bad_ones() -> None:
    find = RemoteTool(
        name="find",
        input_schema={
            "type": "object",
            "properties": {
                "collection": {"type": "string", "pattern": "^(?!system\\.)"},
                "filter": {
                    "type": "object",
                    "properties": {"deletedAt": {"type": ["string", "null"]}},
                },
                "sort": {"enum": ["asc", "desc"]},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["collection"],
        },
    )
    client = FakeClient([find], CallResult(content=("[]",)))
    [tool] = await McpToolProvider(client, prefix="mongodb").tools()

    await tool.run(
        tool.input_model.model_validate({"collection": "recipes", "filter": {"deletedAt": None}})
    )

    assert client.calls == [("find", {"collection": "recipes", "filter": {"deletedAt": None}})]
    with pytest.raises(ValidationError):
        tool.input_model.model_validate({"collection": "system.users"})
    with pytest.raises(ValidationError):
        tool.input_model.model_validate({"collection": "recipes", "sort": "up"})


async def test_a_remote_error_becomes_a_tool_failure() -> None:
    client = FakeClient([FIND], CallResult(content=("read-only mode",), is_error=True))
    [tool] = await McpToolProvider(client, prefix="mongodb").tools()

    with pytest.raises(ToolFailure, match="^read-only mode$"):
        await tool.run(tool.input_model(database="homelab"))


async def test_an_unreachable_server_becomes_a_tool_failure_that_says_so() -> None:
    client = FakeClient([FIND], error=McpUnavailableException("refused"))
    [tool] = await McpToolProvider(client, prefix="mongodb").tools()

    with pytest.raises(ToolFailure, match="may be down or restarting.*refused"):
        await tool.run(tool.input_model(database="homelab"))

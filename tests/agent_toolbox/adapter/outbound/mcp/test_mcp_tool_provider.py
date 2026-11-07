from contextlib import asynccontextmanager
from typing import Any

import pytest
from mcp.types import CallToolResult, ListToolsResult, TextContent
from mcp.types import Tool as McpTool

from agent_toolbox.adapter.inbound.tool_text import call_signature
from agent_toolbox.adapter.outbound.mcp.mcp_backed_tool import McpBackedTool
from agent_toolbox.adapter.outbound.mcp.mcp_tool_provider import McpToolProvider, published_name
from agent_toolbox.domain.exception.tool_failure import ToolFailure

LIST_DATABASES = McpTool(
    name="list-databases",
    description="List every database.",
    input_schema={"type": "object", "properties": {}},
)
FIND = McpTool(
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


class FakeSession:
    def __init__(self, tools: list[McpTool], result: CallToolResult | None = None) -> None:
        self._tools = tools
        self._result = result
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_tools(self) -> ListToolsResult:
        return ListToolsResult(tools=self._tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        self.calls.append((name, arguments))
        assert self._result is not None
        return self._result


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self.fake = session

    @asynccontextmanager
    async def session(self):
        yield self.fake


def provider(session: FakeSession, **options: Any) -> McpToolProvider:
    return McpToolProvider(FakeSessionFactory(session), **options)  # ty: ignore[invalid-argument-type]


def test_published_names_are_prefixed_python_identifiers() -> None:
    assert published_name("mongodb", "list-databases") == "mongodb_list_databases"
    assert published_name("grafana", "search_dashboards") == "grafana_search_dashboards"
    assert published_name("", "collection.schema") == "collection_schema"


async def test_tools_are_published_under_the_prefix_and_keep_their_remote_name() -> None:
    tools = await provider(FakeSession([LIST_DATABASES, FIND]), prefix="mongodb").tools()

    assert [tool.name for tool in tools] == ["mongodb_list_databases", "mongodb_find"]
    assert [tool.remote_name for tool in tools if isinstance(tool, McpBackedTool)] == [
        "list-databases",
        "find",
    ]
    assert call_signature(tools[1]) == "mongodb_find(*, database: str, limit: int | None = 10)"


async def test_the_allowlist_keeps_only_the_named_remote_tools() -> None:
    tools = await provider(
        FakeSession([LIST_DATABASES, FIND]), prefix="mongodb", allowed=["find"]
    ).tools()

    assert [tool.name for tool in tools] == ["mongodb_find"]


async def test_two_servers_with_the_same_tool_name_no_longer_collide() -> None:
    mongo = await provider(FakeSession([FIND]), prefix="mongodb").tools()
    postgres = await provider(FakeSession([FIND]), prefix="postgres").tools()

    assert {tool.name for tool in mongo + postgres} == {"mongodb_find", "postgres_find"}


async def test_a_call_uses_the_remote_name_and_returns_the_text() -> None:
    session = FakeSession(
        [LIST_DATABASES],
        CallToolResult(content=[TextContent(type="text", text="admin, agent_runtime")]),
    )
    [tool] = await provider(session, prefix="mongodb").tools()

    output = await tool.run(tool.input_model())

    assert session.calls == [("list-databases", {})]
    assert output.model_dump() == {"result": "admin, agent_runtime"}


async def test_a_remote_error_becomes_a_tool_failure() -> None:
    session = FakeSession(
        [FIND],
        CallToolResult(content=[TextContent(type="text", text="read-only mode")], is_error=True),
    )
    [tool] = await provider(session, prefix="mongodb").tools()

    with pytest.raises(ToolFailure, match="read-only mode"):
        await tool.run(tool.input_model(database="homelab"))

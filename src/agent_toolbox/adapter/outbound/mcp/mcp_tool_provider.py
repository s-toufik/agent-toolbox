import re
from collections.abc import Collection

from mcp import ListToolsResult

from agent_toolbox.adapter.outbound.mcp.mcp_backed_tool import McpBackedTool
from agent_toolbox.adapter.outbound.mcp.session_factory import McpSessionFactory
from agent_toolbox.application.port.outbound.tool_port import Tool

_NOT_IDENTIFIER = re.compile(r"[^0-9A-Za-z_]")


def published_name(prefix: str, remote_name: str) -> str:
    safe: str = _NOT_IDENTIFIER.sub("_", remote_name)
    return f"{prefix}_{safe}" if prefix else safe


class McpToolProvider:
    def __init__(
        self,
        session_factory: McpSessionFactory,
        prefix: str = "",
        allowed: Collection[str] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._prefix = prefix
        self._allowed: frozenset[str] | None = frozenset(allowed) if allowed else None

    async def tools(self) -> list[Tool]:
        async with self._session_factory.session() as session:
            listed: ListToolsResult = await session.list_tools()
        return [
            McpBackedTool(
                self._session_factory,
                published_name(self._prefix, tool.name),
                tool.description or "",
                tool.input_schema,
                tool.output_schema,
                remote_name=tool.name,
            )
            for tool in listed.tools
            if self._allowed is None or tool.name in self._allowed
        ]

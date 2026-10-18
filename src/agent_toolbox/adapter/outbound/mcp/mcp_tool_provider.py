from mcp import ListToolsResult

from agent_toolbox.adapter.outbound.mcp.mcp_backed_tool import McpBackedTool
from agent_toolbox.adapter.outbound.mcp.session_factory import McpSessionFactory
from agent_toolbox.application.port.outbound.tool_port import Tool


class McpToolProvider:
    def __init__(self, session_factory: McpSessionFactory) -> None:
        self._session_factory = session_factory

    async def tools(self) -> list[Tool]:
        async with self._session_factory.session() as session:
            listed: ListToolsResult = await session.list_tools()
        return [
            McpBackedTool(
                self._session_factory,
                tool.name,
                tool.description or "",
                tool.input_schema,
                tool.output_schema,
            )
            for tool in listed.tools
        ]

from collections.abc import Awaitable, Callable
from typing import Any

from pycraftcore.mcp import ServedTool, ToolCallError, ToolServer

from agent_toolbox.adapter.inbound.tool_text import described
from agent_toolbox.application.port.inbound.invoke_tool_port import InvokeToolPort
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure


class ToolBinder:
    def __init__(self, invoker: InvokeToolPort) -> None:
        self._invoker = invoker

    def bind(self, server: ToolServer) -> list[str]:
        for tool in self._invoker.tools:
            self.bind_one(server, tool)
        return [tool.name for tool in self._invoker.tools]

    def bind_one(self, server: ToolServer, tool: Tool) -> None:
        server.add_tool(
            ServedTool(
                tool.name,
                described(tool),
                tool.input_model,
                tool.output_model,
                self._handler(tool.name),
            )
        )

    @staticmethod
    def unbind(server: ToolServer, name: str) -> None:
        server.remove_tool(name)

    def _handler(self, name: str) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
        invoker = self._invoker

        async def handle(arguments: dict[str, Any]) -> dict[str, Any]:
            try:
                return await invoker.invoke(name, arguments)
            except ToolFailure as failure:
                raise ToolCallError(str(failure)) from failure

        return handle

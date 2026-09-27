import inspect
from collections.abc import Callable
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from agent_toolbox.adapter.inbound.tool_text import described
from agent_toolbox.application.port.inbound.invoke_tool_port import InvokeToolPort
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure


class ToolBinder:
    def __init__(self, invoker: InvokeToolPort) -> None:
        self._invoker = invoker

    def bind(self, server: MCPServer) -> list[str]:
        for tool in self._invoker.tools:
            server.add_tool(
                self._handler(tool),
                name=tool.name,
                description=described(tool),
                structured_output=True,
            )
        return [tool.name for tool in self._invoker.tools]

    def _handler(self, tool: Tool) -> Callable[..., Any]:
        invoker = self._invoker

        async def handler(**arguments: Any) -> Any:
            try:
                return await invoker.invoke(tool.name, arguments)
            except ToolFailure as failure:
                raise ToolError(str(failure)) from failure

        # MCP builds the input schema from the signature and the output schema from the
        # return annotation, so both come from the tool's own models.
        parameters: list[inspect.Parameter] = [
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Annotated[field.annotation, field],
                default=inspect.Parameter.empty if field.is_required() else field.default,
            )
            for name, field in tool.input_model.model_fields.items()
        ]
        handler.__name__ = tool.name
        handler.__signature__ = inspect.Signature(  # ty: ignore[unresolved-attribute]
            parameters, return_annotation=tool.output_model
        )
        handler.__annotations__ = {parameter.name: parameter.annotation for parameter in parameters}
        handler.__annotations__["return"] = tool.output_model
        return handler

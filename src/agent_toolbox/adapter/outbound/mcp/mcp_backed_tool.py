from typing import Any

from pycraftcore.mcp import CallResult, McpClient, McpUnavailableException, RemoteTool
from pycraftcore.mcp.adapter import model_from_schema
from pydantic import BaseModel

from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure


class McpBackedTool(Tool[BaseModel, BaseModel]):
    def __init__(self, client: McpClient, remote: RemoteTool, name: str) -> None:
        self._client = client
        self.remote_name = remote.name
        self.name = name
        self.description = remote.description
        self.input_model = model_from_schema(f"{name}_input", remote.input_schema)
        self.output_model = model_from_schema(f"{name}_output", remote.output_schema)

    async def run(self, arguments: BaseModel) -> BaseModel:
        try:
            result: CallResult = await self._client.call_tool(
                self.remote_name, arguments.model_dump(exclude_unset=True)
            )
        except McpUnavailableException as error:
            raise ToolFailure(
                f"MCP call '{self.remote_name}' failed, its server may be down or restarting; "
                f"try again later: {error}"
            ) from error
        if result.is_error:
            raise ToolFailure(result.text)
        payload: Any = (
            result.structured if result.structured is not None else {"result": result.text}
        )
        return self.output_model.model_validate(payload)

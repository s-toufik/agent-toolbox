from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel

from agent_toolbox.adapter.outbound.mcp.schema_model import model_from_schema
from agent_toolbox.adapter.outbound.mcp.session_factory import McpSessionFactory
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure


class McpBackedTool(Tool[BaseModel, BaseModel]):
    def __init__(
        self,
        session_factory: McpSessionFactory,
        name: str,
        description: str,
        input_schema: dict[str, Any] | None,
        output_schema: dict[str, Any] | None,
    ) -> None:
        self._session_factory = session_factory
        self.name = name
        self.description = description
        self.input_model = model_from_schema(f"{name}_input", input_schema)
        self.output_model = model_from_schema(f"{name}_output", output_schema)

    async def run(self, arguments: BaseModel) -> BaseModel:
        try:
            async with self._session_factory.session() as session:
                result: CallToolResult = await session.call_tool(
                    self.name, arguments.model_dump(exclude_none=True)
                )
        except Exception as exception:
            raise ToolFailure(f"MCP call '{self.name}' failed: {exception}") from exception
        if result.is_error:
            raise ToolFailure(_stringify(result.content))
        payload: Any = (
            result.structured_content
            if result.structured_content is not None
            else {"result": _stringify(result.content)}
        )
        return self.output_model.model_validate(payload)


def _stringify(content: list[Any]) -> str:
    return "\n".join(
        block.text if isinstance(block, TextContent) else str(block) for block in content
    )

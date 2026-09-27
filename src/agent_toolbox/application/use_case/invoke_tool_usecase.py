import traceback
from collections.abc import Iterable, Mapping
from typing import Any

from pycraftcore.logger.port import Logger
from pydantic import BaseModel, ValidationError

from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.exception.unknown_tool_exception import UnknownToolException


class InvokeToolUseCase:
    def __init__(self, tools: Iterable[Tool], logger: Logger) -> None:
        self._tools: dict[str, Tool] = {tool.name: tool for tool in tools}
        self._logger = logger

    @property
    def tools(self) -> tuple[Tool, ...]:
        return tuple(self._tools.values())

    async def invoke(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        self._logger.info(f"tool '{name}' invoked")

        try:
            output: BaseModel = await self._run(name, arguments)
        except ToolFailure as failure:
            self._logger.warning(f"tool '{name}': {failure}")
            raise
        except Exception as exception:
            traceback_str: str = "".join(traceback.format_exception(exception))
            self._logger.error(f"tool '{name}' raised:\n{traceback_str}")
            raise ToolFailure(f"Tool execution failed: {exception}") from exception

        return output.model_dump(mode="json")

    async def _run(self, name: str, arguments: Mapping[str, Any]) -> BaseModel:
        tool: Tool | None = self._tools.get(name)
        if tool is None:
            raise UnknownToolException(f"Unknown tool: '{name}'.")

        provided: dict[str, Any] = {
            key: value for key, value in arguments.items() if value is not None
        }

        try:
            validated: BaseModel = tool.input_model.model_validate(provided)
        except ValidationError as error:
            raise ToolFailure(_describe(name, error)) from error

        return await tool.run(validated)


def _describe(name: str, error: ValidationError) -> str:
    problems: str = "; ".join(
        f"{'.'.join(str(part) for part in detail['loc']) or 'arguments'}: {detail['msg']}"
        for detail in error.errors()
    )
    return f"Invalid arguments for '{name}': {problems}"

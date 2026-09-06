import inspect
import uuid
from collections.abc import Callable
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pycraftcore.http.context.request_context import request_id_context
from pydantic import Field

from agent_toolbox.application.port.outbound.tool_port import ToolRegistryPort
from agent_toolbox.application.use_case.execute_tool_usecase import ExecuteToolUseCase
from agent_toolbox.domain.enum.parameter_type import ParameterType
from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome
from agent_toolbox.domain.model.tool_specification import ToolParameter, ToolSpecification

_PYTHON_TYPE: dict[ParameterType, type] = {
    ParameterType.STRING: str,
    ParameterType.INTEGER: int,
    ParameterType.NUMBER: float,
    ParameterType.BOOLEAN: bool,
}


class ToolBinder:
    def __init__(self, use_case: ExecuteToolUseCase, registry: ToolRegistryPort) -> None:
        self._use_case = use_case
        self._registry = registry

    def bind(self, server: MCPServer) -> list[str]:
        bound: list[str] = []
        for specification in self._registry.specifications():
            server.add_tool(
                self._handler(specification),
                name=specification.name,
                description=specification.description,
            )
            bound.append(specification.name)
        return bound

    def _handler(self, specification: ToolSpecification) -> Callable[..., Any]:
        use_case = self._use_case

        async def handler(**arguments: Any) -> str:
            outcome: ToolOutcome = await use_case.execute(
                ToolInvocation(
                    id=_invocation_id(),
                    name=specification.name,
                    arguments={key: value for key, value in arguments.items() if value is not None},
                )
            )

            if outcome.failed and not outcome.output:
                raise ToolError(outcome.error or "Tool failed")
            return outcome.content

        handler.__name__ = specification.name
        handler.__doc__ = specification.description
        handler.__signature__ = _signature(specification.parameters)  # ty: ignore[unresolved-attribute]
        handler.__annotations__ = _annotations(specification.parameters)
        return handler


def _signature(parameters: tuple[ToolParameter, ...]) -> inspect.Signature:
    return inspect.Signature(
        [
            inspect.Parameter(
                parameter.name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=_annotation(parameter),
                default=inspect.Parameter.empty if parameter.required else None,
            )
            for parameter in parameters
        ],
        return_annotation=str,
    )


def _annotations(parameters: tuple[ToolParameter, ...]) -> dict[str, Any]:
    return {parameter.name: _annotation(parameter) for parameter in parameters} | {"return": str}


def _annotation(parameter: ToolParameter) -> Any:
    python_type = _PYTHON_TYPE[parameter.type]
    return Annotated[python_type, Field(description=parameter.description)]  # ty: ignore[invalid-type-form]


def _invocation_id() -> str:
    return request_id_context.get() or f"call_{uuid.uuid4().hex[:8]}"

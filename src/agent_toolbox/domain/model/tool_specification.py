from dataclasses import dataclass

from agent_toolbox.domain.enum.parameter_type import ParameterType


@dataclass(frozen=True, slots=True)
class ToolParameter:
    name: str
    type: ParameterType
    description: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class ToolSpecification:
    name: str
    description: str
    parameters: tuple[ToolParameter, ...] = ()

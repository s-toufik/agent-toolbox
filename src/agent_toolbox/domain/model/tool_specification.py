from dataclasses import dataclass
from typing import Any

from agent_toolbox.domain.enum.parameter_type import ParameterType


@dataclass(frozen=True, slots=True)
class ToolParameter:
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Any = None


@dataclass(frozen=True, slots=True)
class ToolSpecification:
    name: str
    description: str
    parameters: tuple[ToolParameter, ...] = ()

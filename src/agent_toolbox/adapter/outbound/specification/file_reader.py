import sys

from agent_toolbox.domain.enum.parameter_type import ParameterType
from agent_toolbox.domain.model.tool_specification import ToolParameter, ToolSpecification

SPECIFICATION = ToolSpecification(
    name="file_reader",
    description=(
        "This is a file reader tool. It reads a file and returns its contents. "
        "Supported file formats: yml, csv, json "
        f"Current system: {sys.platform}"
    ),
    parameters=(
        ToolParameter(
            name="file_path",
            type=ParameterType.STRING,
            description="Absolute file path to read including extension.",
            required=True,
        ),
    ),
)

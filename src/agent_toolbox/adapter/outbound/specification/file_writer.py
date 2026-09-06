import sys

from agent_toolbox.domain.enum.parameter_type import ParameterType
from agent_toolbox.domain.model.tool_specification import ToolParameter, ToolSpecification

SPECIFICATION = ToolSpecification(
    name="file_writer",
    description=(
        "This is a file writer tool. It takes a file path as input and writes data to it. "
        "Supported file formats: yml, csv, json "
        f"Current system: {sys.platform}. "
        f""
    ),
    parameters=(
        ToolParameter(
            name="file_path",
            type=ParameterType.STRING,
            description="Absolute file path to write including extension.",
            required=True,
        ),
        ToolParameter(
            name="data",
            type=ParameterType.STRING,
            description=(
                "Data to be written to file, encoded as a JSON string. "
                "For csv, the JSON must decode to a list of objects; "
                "for the other extensions, it must decode to a single object."
            ),
            required=True,
        ),
    ),
)

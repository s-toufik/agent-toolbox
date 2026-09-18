import sys

from agent_toolbox.domain.enum.parameter_type import ParameterType
from agent_toolbox.domain.model.tool_specification import ToolParameter, ToolSpecification

SPECIFICATION = ToolSpecification(
    name="file_reader",
    description=(
        "This is a file reader tool. It reads a file and returns its contents. "
        "Supported file formats: yml, yaml, json, csv, json, md, txt"
        f"Current system: {sys.platform}"
    ),
    parameters=(
        ToolParameter(
            name="file_path",
            type=ParameterType.STRING,
            description="Absolute file path to read including extension.",
            required=True,
        ),
        ToolParameter(
            name="start",
            type=ParameterType.INTEGER,
            description="line number to start reading file from.",
            required=False,
        ),
        ToolParameter(
            name="count",
            type=ParameterType.INTEGER,
            description="maximum number of lines to read.",
            required=False,
        ),
    ),
    returns=(
        "str (txt, md), object (json, yml/yaml), array of objects with string values (csv), "
        "or array of str (when start/count are given, one entry per line)."
    ),
)

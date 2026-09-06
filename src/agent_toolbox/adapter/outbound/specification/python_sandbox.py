from pycraftcore.runtime.adapter.python.adapter import PYTHON_ALLOWLIST

from agent_toolbox.domain.enum.parameter_type import ParameterType
from agent_toolbox.domain.model.tool_specification import ToolParameter, ToolSpecification

TIMEOUT_SECONDS: int = 100
MAX_MEMORY_MB: int = 256
MAX_CONCURRENCY: int = 8

SPECIFICATION = ToolSpecification(
    name="python_executor",
    description=(
        "Execute Python code for data analysis or computation. "
        f"Allowed modules: {', '.join(sorted(PYTHON_ALLOWLIST))}. "
        "Assign your final value to a variable named 'result'; "
        "if returning a result is not relevant, set result='no return'. "
        f"Hard timeout: {TIMEOUT_SECONDS} seconds."
    ),
    parameters=(
        ToolParameter(
            name="code",
            type=ParameterType.STRING,
            description="Python source code to run in a sandbox.",
            required=True,
        ),
    ),
)

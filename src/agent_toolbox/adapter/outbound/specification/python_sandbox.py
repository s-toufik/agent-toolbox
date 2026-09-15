from pycraftcore.runtime.adapter.python.python_runner_template import PYTHON_ALLOWLIST

from agent_toolbox.domain.enum.parameter_type import ParameterType
from agent_toolbox.domain.model.tool_specification import ToolParameter, ToolSpecification

TIMEOUT_SECONDS: int = 18000
MAX_MEMORY_MB: int = 256
MAX_CONCURRENCY: int = 8

_BASE_DESCRIPTION = (
    "Execute Python code for data analysis or computation. "
    f"Allowed modules: {', '.join(sorted(PYTHON_ALLOWLIST))}. "
    "Assign your final value to a variable named 'result'; "
    "if returning a result is not relevant, set result='no return'. "
    f"Hard timeout: {TIMEOUT_SECONDS} seconds."
)

_VAULT_DESCRIPTION = (
    "This tool is where heavy file analysis and generation belongs; the file_reader "
    "and file_writer tools are only for quick inspection and small writes. A shared "
    "vault directory is mounted as your working directory and exposed to your code as "
    "the 'VAULT' variable: read every input file from it and write every output there, "
    "using relative paths or the VAULT variable. File access outside the vault is denied. "
    "Vault Location: {vault_path}."
)

_TOOLS_DESCRIPTION = (
    "Inside your code these toolbox tools are available as functions that return the "
    "tool's text output (optional arguments show their default value): {functions}. "
    "Call them with keyword arguments and parse results with json.loads when needed; "
    "a failing tool raises an exception."
)


def _description(
    vault_path: str | None,
    tool_functions: tuple[str, ...],
) -> str:
    text = _BASE_DESCRIPTION

    if vault_path:
        text += _VAULT_DESCRIPTION.format(vault_path=vault_path)

    if tool_functions:
        text += _TOOLS_DESCRIPTION.format(functions=", ".join(tool_functions))

    return text


def specification(
    vault_path: str | None = None,
    tool_functions: tuple[str, ...] = (),
) -> ToolSpecification:
    return ToolSpecification(
        name="python_executor",
        description=_description(vault_path, tool_functions),
        parameters=(
            ToolParameter(
                name="code",
                type=ParameterType.STRING,
                description=(
                    "Python source code to run in a sandbox. Assign your final value "
                    "to a variable named 'result'; otherwise set result='no return'."
                ),
                required=True,
            ),
        ),
    )

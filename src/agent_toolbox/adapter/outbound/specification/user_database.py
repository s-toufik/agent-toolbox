from pycraftcore.query_language.constants import FORBIDDEN_SQL_EXPRESSIONS

from agent_toolbox.domain.enum.parameter_type import ParameterType
from agent_toolbox.domain.model.tool_specification import ToolParameter, ToolSpecification

CONNECTOR_NAME: str = "users"
DIALECT: str = "sqlite"

SPECIFICATION = ToolSpecification(
    name="users_tables",
    description=(
        "Execute read-only SQL queries against the service database, which holds "
        "service information such as the users dashboard and payment data. "
        f"Defaults to the {DIALECT} dialect. Forbidden operations: "
        f"{', '.join(item.__name__ for item in FORBIDDEN_SQL_EXPRESSIONS)}."
    ),
    parameters=(
        ToolParameter(
            name="query",
            type=ParameterType.STRING,
            description="SQL query to execute.",
            required=True,
        ),
        ToolParameter(
            name="dialect",
            type=ParameterType.STRING,
            description=f"sqlglot source dialect. Defaults to {DIALECT}.",
            required=False,
        ),
    ),
)

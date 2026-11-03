import asyncio
from typing import Any

from pycraftcore.query_language.constants import FORBIDDEN_SQL_EXPRESSIONS
from pycraftcore.query_language.port import QueryFactory, QueryHandler
from pycraftcore.repository.port import AsyncRepository

from agent_toolbox.adapter.outbound.sql.model.sql_query_input import QueryUsersInput
from agent_toolbox.adapter.outbound.sql.model.sql_query_output import QueryUsersOutput
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure


class QueryUsers(Tool[QueryUsersInput, QueryUsersOutput]):
    name = "users_tables"
    description = (
        "Execute read-only SQL queries against the service database, which holds service "
        "information such as the users dashboard and payment data. Forbidden operations: "
        f"{', '.join(item.__name__ for item in FORBIDDEN_SQL_EXPRESSIONS)}."
    )
    input_model = QueryUsersInput
    output_model = QueryUsersOutput

    def __init__(self, repository: AsyncRepository, query_factory: QueryFactory) -> None:
        self._repository = repository
        self._query_factory = query_factory

    async def run(self, arguments: QueryUsersInput) -> QueryUsersOutput:
        if not arguments.query.strip():
            raise ToolFailure("No SQL query provided.")

        try:
            handler: QueryHandler = self._query_factory(arguments.query, dialect=arguments.dialect)
            statement: str = await asyncio.to_thread(handler.transpile)
        except Exception as error:
            raise ToolFailure(f"SQL validation error ({arguments.dialect}): {error}") from error

        try:
            rows: list[dict[str, Any]] = await self._repository.execute(statement)
        except Exception as error:
            raise ToolFailure(f"SQL execution error: {error}") from error

        return QueryUsersOutput(rows=rows)

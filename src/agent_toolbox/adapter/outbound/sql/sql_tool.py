import asyncio
from typing import Any

from pycraftcore.query_language.port import QueryFactory, QueryHandler
from pycraftcore.repository.port import AsyncRepository

from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome
from agent_toolbox.domain.model.tool_specification import ToolSpecification


class SqlTool:
    def __init__(
        self,
        repository: AsyncRepository,
        query_factory: QueryFactory,
        specification: ToolSpecification,
        default_dialect: str,
    ) -> None:
        self._repository = repository
        self._query_factory = query_factory
        self._specification = specification
        self._default_dialect = default_dialect

    @property
    def specification(self) -> ToolSpecification:
        return self._specification

    async def invoke(self, invocation: ToolInvocation) -> ToolOutcome:
        query: str = invocation.argument("query", "") or ""
        dialect: str = invocation.argument("dialect") or self._default_dialect

        if not query.strip():
            return ToolOutcome.failure(invocation, "No SQL query provided.")

        try:
            handler: QueryHandler = self._query_factory(query, dialect=dialect)
            statement: str = await asyncio.to_thread(handler.transpile)
        except Exception as exception:
            return ToolOutcome.failure(invocation, f"SQL validation error ({dialect}): {exception}")

        try:
            rows: list[dict[str, Any]] = await self._repository.execute(statement)
        except Exception as exception:
            return ToolOutcome.failure(invocation, f"SQL execution error: {exception}")

        return ToolOutcome.success(invocation, str(rows))

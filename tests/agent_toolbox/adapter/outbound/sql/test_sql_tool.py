import pytest

from agent_toolbox.adapter.outbound.sql.model.sql_query_input import QueryUsersInput
from agent_toolbox.adapter.outbound.sql.model.sql_query_output import QueryUsersOutput
from agent_toolbox.adapter.outbound.sql.sql_tool import QueryUsers
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from tests.agent_toolbox.stubs import StubRepository, query_factory


async def test_runs_the_transpiled_statement_and_returns_rows() -> None:
    repository = StubRepository(rows=[{"id": 1}])

    output = await QueryUsers(repository, query_factory()).run(QueryUsersInput(query="SELECT 1"))

    assert repository.executed == ["TRANSPILED SELECT 1"]
    assert output == QueryUsersOutput(rows=[{"id": 1}])


def test_dialect_defaults_to_sqlite() -> None:
    assert QueryUsersInput(query="SELECT 1").dialect == "sqlite"


async def test_invalid_sql_never_reaches_the_database() -> None:
    repository = StubRepository()
    tool = QueryUsers(repository, query_factory(error=ValueError("DROP is forbidden")))

    with pytest.raises(ToolFailure, match=r"SQL validation error \(sqlite\): DROP is forbidden"):
        await tool.run(QueryUsersInput(query="DROP TABLE users"))

    assert repository.executed == []


async def test_empty_query_is_rejected() -> None:
    with pytest.raises(ToolFailure, match="No SQL query provided."):
        await QueryUsers(StubRepository(), query_factory()).run(QueryUsersInput(query=" "))


async def test_database_errors_are_reported() -> None:
    tool = QueryUsers(StubRepository(error=RuntimeError("no such table")), query_factory())

    with pytest.raises(ToolFailure, match="SQL execution error: no such table"):
        await tool.run(QueryUsersInput(query="SELECT 1"))

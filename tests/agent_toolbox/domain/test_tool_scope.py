import pytest

from agent_toolbox.domain.model.tool_scope import ALL_TOOLS, ToolScope


def test_a_scope_holds_the_tools_its_patterns_match() -> None:
    observation = ToolScope("observation", ("grafana_*", "users_tables"))

    assert observation.includes("grafana_search_dashboards")
    assert observation.includes("users_tables")
    assert not observation.includes("postgres_execute_sql")
    assert not observation.includes("Grafana_search")


def test_a_scope_without_patterns_holds_no_shared_tool() -> None:
    assert not ToolScope("kitchen").includes("file_reader")


def test_all_holds_every_tool() -> None:
    assert ALL_TOOLS.is_all and ALL_TOOLS.includes("anything")


@pytest.mark.parametrize(
    ("name", "patterns", "message"),
    [
        ("Observation", (), "lower case"),
        ("all", ("grafana_*",), "built in"),
        ("analysis", ("postgres_*", " "), "empty pattern"),
    ],
)
def test_a_scope_that_cannot_work_is_refused(name, patterns, message) -> None:
    with pytest.raises(ValueError, match=message):
        ToolScope(name, patterns)

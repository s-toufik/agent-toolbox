import pytest

from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from tests.agent_toolbox.stubs import Named


def names(catalog) -> list[str]:
    return [tool.name for tool in catalog.tools]


def test_fixed_tools_keep_their_order_and_refuse_a_duplicate() -> None:
    catalog = ToolCatalog([Named("a"), Named("b")])

    assert names(catalog) == ["a", "b"]
    with pytest.raises(ValueError, match="Duplicate tool name: 'a'"):
        catalog.add(Named("a"))


def test_a_source_s_tools_are_added_then_replaced_by_its_next_list() -> None:
    catalog = ToolCatalog([Named("files")])

    first = catalog.replace("grafana", [Named("grafana_search"), Named("grafana_query")])
    second = catalog.replace("grafana", [Named("grafana_search"), Named("grafana_alerts")])

    assert [tool.name for tool in first.added] == ["grafana_search", "grafana_query"]
    assert [tool.name for tool in second.added] == ["grafana_alerts"]
    assert second.removed == ("grafana_query",)
    assert names(catalog) == ["files", "grafana_search", "grafana_alerts"]


def test_the_same_list_again_is_no_change() -> None:
    catalog = ToolCatalog()
    catalog.replace("grafana", [Named("grafana_search")])

    assert not catalog.replace("grafana", [Named("grafana_search")])


def test_a_tool_whose_description_changed_is_republished() -> None:
    catalog = ToolCatalog()
    catalog.replace("grafana", [Named("grafana_search", "old")])

    change = catalog.replace("grafana", [Named("grafana_search", "new")])

    assert change.removed == ("grafana_search",)
    assert [tool.description for tool in change.added] == ["new"]
    tool = catalog.get("grafana_search")
    assert tool is not None and tool.description == "new"


def test_a_name_another_source_owns_is_skipped_as_a_conflict() -> None:
    catalog = ToolCatalog([Named("file_reader")])
    catalog.replace("mongodb", [Named("shared")])

    change = catalog.replace("postgres", [Named("shared"), Named("file_reader"), Named("pg")])

    assert change.conflicts == ("shared", "file_reader")
    assert [tool.name for tool in change.added] == ["pg"]


def test_a_view_hides_the_named_tools_but_follows_the_catalog() -> None:
    catalog = ToolCatalog([Named("python_executor"), Named("files")])
    view = catalog.without("python_executor")

    catalog.replace("grafana", [Named("grafana_search")])

    assert names(view) == ["files", "grafana_search"]
    assert view.get("python_executor") is None

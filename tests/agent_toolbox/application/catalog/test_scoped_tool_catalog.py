from agent_toolbox.application.catalog.scoped_tool_catalog import ScopedToolCatalog
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.domain.model.tool_scope import ToolScope
from tests.agent_toolbox.stubs import Named

OBSERVATION = ToolScope("observation", ("grafana_*",))


def test_the_view_shows_only_the_scope_s_tools_and_its_own_first() -> None:
    catalog = ToolCatalog([Named("grafana_search"), Named("file_reader")])
    python = Named("python_executor")

    view = ScopedToolCatalog(catalog, OBSERVATION, own=(python,))

    assert [tool.name for tool in view.tools] == ["python_executor", "grafana_search"]
    assert view.get("python_executor") is python
    assert view.get("grafana_search") is catalog.get("grafana_search")
    assert view.get("file_reader") is None


def test_the_view_follows_the_catalog_as_tools_come_and_go() -> None:
    catalog = ToolCatalog()
    view = ScopedToolCatalog(catalog, OBSERVATION)

    catalog.replace("grafana", [Named("grafana_search"), Named("postgres_sql")])
    added = [tool.name for tool in view.tools]
    catalog.replace("grafana", [])

    assert added == ["grafana_search"]
    assert view.tools == ()

from agent_toolbox.application.catalog.aliased_tool import AliasedTool
from agent_toolbox.application.catalog.scoped_tool_catalog import ScopedToolCatalog
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.domain.model.tool_scope import ToolAlias, ToolScope
from tests.agent_toolbox.stubs import Find, Named

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


RECIPES_FIND = ToolAlias(
    "recipes_find", "mongodb_find", fixed={"database": "kitchen", "collection": "recipes"}
)
KITCHEN = ToolScope("kitchen", ("python_executor", "file_*"), (RECIPES_FIND,))


def test_aliases_come_after_the_scope_s_own_tools_and_before_the_shared_ones() -> None:
    catalog = ToolCatalog([Named("file_reader"), Find(), Named("grafana_search")])
    python = Named("python_executor")

    view = ScopedToolCatalog(catalog, KITCHEN, own=(python,))

    assert [tool.name for tool in view.tools] == ["python_executor", "recipes_find", "file_reader"]
    recipes = view.get("recipes_find")
    assert isinstance(recipes, AliasedTool) and recipes.target is catalog.get("mongodb_find")
    assert view.get("mongodb_find") is None


def test_an_alias_is_built_once_while_its_tool_stays_the_same() -> None:
    view = ScopedToolCatalog(ToolCatalog([Find()]), KITCHEN)

    assert view.get("recipes_find") is view.tools[0]
    assert view.get("recipes_find") is view.get("recipes_find")


def test_an_alias_follows_its_tool_as_it_comes_goes_and_changes() -> None:
    catalog = ToolCatalog()
    view = ScopedToolCatalog(catalog, KITCHEN)

    missing = (view.tools, view.get("recipes_find"), view.unresolved_aliases)
    catalog.replace("mongodb", [Find()])
    first = view.get("recipes_find")
    catalog.replace("mongodb", [Find()])
    second = view.get("recipes_find")
    catalog.replace("mongodb", [])

    assert missing == (
        (),
        None,
        {"recipes_find": "alias 'recipes_find': its tool 'mongodb_find' is not in the catalog"},
    )
    assert first is not None and second is not None and first is not second
    assert second.target is not first.target
    assert view.get("recipes_find") is None


def test_a_lock_that_cannot_be_built_never_falls_back_to_the_tool_it_locks() -> None:
    locked = ToolAlias("mongodb_find", "mongodb_find", fixed={"database": "kitchen", "limit": "x"})
    view = ScopedToolCatalog(ToolCatalog([Find()]), ToolScope("kitchen", (), (locked,)))

    assert view.get("mongodb_find") is None
    assert view.tools == ()
    assert view.unresolved_aliases == {
        "mongodb_find": "alias 'mongodb_find': fixed arguments don't fit 'mongodb_find': "
        "limit: Input should be a valid integer, unable to parse string as an integer"
    }


def test_a_scope_whose_aliases_all_resolve_reports_nothing() -> None:
    view = ScopedToolCatalog(ToolCatalog([Find()]), KITCHEN)

    assert view.unresolved_aliases == {}

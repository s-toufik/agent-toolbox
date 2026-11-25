import pytest

from agent_toolbox.domain.model.tool_scope import ALL_TOOLS, ToolAlias, ToolScope


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


RECIPES_FIND = ToolAlias(
    "recipes_find", "mongodb_find", fixed={"database": "kitchen", "collection": "recipes"}
)
INGREDIENTS_FIND = ToolAlias(
    "ingredients_find", "mongodb_find", fixed={"database": "kitchen", "collection": "ingredients"}
)
RECIPES_SCHEMA = ToolAlias("recipes_schema", "mongodb_collection_schema")


def kitchen(*aliases: ToolAlias, patterns: tuple[str, ...] = ("python_executor",)) -> ToolScope:
    return ToolScope("kitchen", patterns, aliases)


def test_an_alias_has_no_description_or_fixed_arguments_by_default() -> None:
    alias = ToolAlias("recipes_schema", "mongodb_collection_schema")

    assert (alias.description, dict(alias.fixed)) == (None, {})


def test_the_fixed_arguments_of_an_alias_are_read_only_and_its_own() -> None:
    source = {"database": "kitchen", "filter": {"tags": ["vegan"]}}
    alias = ToolAlias("recipes_find", "mongodb_find", fixed=source)
    source["database"] = "billing"
    source["filter"]["tags"].append("cheap")

    assert alias.fixed == {"database": "kitchen", "filter": {"tags": ["vegan"]}}
    with pytest.raises(TypeError):
        alias.fixed["database"] = "billing"  # ty: ignore[invalid-assignment]


@pytest.mark.parametrize(
    "name", ["recipes-find", "recipes.find", "1st_recipe", "class", "", "recipes find", "find\n"]
)
def test_an_alias_sandbox_code_could_not_call_is_refused(name: str) -> None:
    with pytest.raises(ValueError, match="must be a Python identifier"):
        ToolAlias(name, "mongodb_find")


@pytest.mark.parametrize(
    "name",
    ["print", "list", "open", "ToolError", "WORKING_DIRECTORY", "result", "__builtins__", "__x__"],
)
def test_an_alias_named_like_something_the_sandbox_already_binds_is_refused(name: str) -> None:
    with pytest.raises(ValueError, match=f"name '{name}' is already a name in the sandbox"):
        ToolAlias(name, "mongodb_find")


@pytest.mark.parametrize(
    "target", ["my-grafana_search_dashboards", "1password_get_item", "jira.search", "global"]
)
def test_an_alias_gives_a_callable_name_to_a_catalog_tool_sandbox_code_could_not_call(
    target: str,
) -> None:
    assert ToolAlias("search", target).target == target


@pytest.mark.parametrize("target", ["", "mongodb find", "mongodb/find", "mongodb_find\n"])
def test_an_alias_built_on_something_that_cannot_be_a_tool_name_is_refused(target: str) -> None:
    with pytest.raises(ValueError, match="'recipes_find': target .* must be letters, digits"):
        ToolAlias("recipes_find", target)


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"description": " "}, "description must not be blank"),
        ({"fixed": {" ": "kitchen"}}, "fixed argument names must not be blank"),
    ],
)
def test_an_alias_with_a_blank_description_or_argument_name_is_refused(values, message) -> None:
    with pytest.raises(ValueError, match=message):
        ToolAlias("recipes_find", "mongodb_find", **values)


def test_a_scope_finds_its_aliases_by_name() -> None:
    scope = kitchen(RECIPES_FIND, RECIPES_SCHEMA, INGREDIENTS_FIND)

    assert scope.alias("recipes_find") is RECIPES_FIND
    assert scope.alias("mongodb_find") is None


def test_a_pattern_includes_catalog_tools_and_an_alias_does_not() -> None:
    scope = kitchen(RECIPES_FIND)

    assert scope.includes("python_executor")
    assert not scope.includes("recipes_find")
    assert not scope.includes("mongodb_find")


def test_an_alias_may_keep_the_name_of_the_tool_it_is_built_on() -> None:
    locked = ToolAlias("mongodb_find", "mongodb_find", fixed={"database": "kitchen"})

    assert kitchen(locked).alias("mongodb_find") is locked


def test_a_locked_tool_can_still_be_the_base_of_other_aliases_in_the_scope() -> None:
    locked = ToolAlias("mongodb_find", "mongodb_find", fixed={"database": "kitchen"})

    scope = kitchen(locked, RECIPES_FIND)

    assert (scope.alias("mongodb_find"), scope.alias("recipes_find")) == (locked, RECIPES_FIND)


def test_a_scope_with_aliases_can_key_its_mcp_server() -> None:
    scope = kitchen(RECIPES_FIND, RECIPES_SCHEMA)

    servers = {scope: "kitchen-server"}

    assert servers[kitchen(RECIPES_FIND, RECIPES_SCHEMA)] == "kitchen-server"


@pytest.mark.parametrize(
    ("scope", "message"),
    [
        (
            lambda: kitchen(RECIPES_FIND, ToolAlias("recipes_find", "mongodb_aggregate")),
            "'kitchen': aliases named more than once: recipes_find$",
        ),
        (
            lambda: kitchen(RECIPES_FIND, patterns=("recipes_*",)),
            "'kitchen': aliases whose name a pattern also matches.*: recipes_find$",
        ),
        (
            lambda: kitchen(
                ToolAlias("vegan_find", "recipes_find", fixed={"filter": {"vegan": True}}),
                RECIPES_FIND,
            ),
            "'kitchen': aliases built on another alias of the scope: vegan_find$",
        ),
        (lambda: ToolScope("all", ("*",), (RECIPES_FIND,)), "built in"),
    ],
)
def test_a_scope_whose_aliases_contradict_each_other_is_refused(scope, message) -> None:
    with pytest.raises(ValueError, match=message):
        scope()


def test_every_alias_named_twice_is_named_in_one_message() -> None:
    with pytest.raises(ValueError, match="more than once: ingredients_find, recipes_find$"):
        kitchen(RECIPES_FIND, INGREDIENTS_FIND, INGREDIENTS_FIND, RECIPES_FIND)

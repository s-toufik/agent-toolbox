import pytest
from pydantic import ValidationError, create_model

from agent_toolbox.application.catalog.aliased_tool import AliasedTool
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.tool_scope import ToolAlias
from tests.agent_toolbox.stubs import Find, Open

RECIPES_FIND = ToolAlias(
    "recipes_find",
    "mongodb_find",
    description="Find recipes.",
    fixed={"database": "kitchen", "collection": "recipes"},
)


def test_an_aliased_tool_is_published_under_the_alias_name_and_description() -> None:
    find = Find()

    tool = AliasedTool(RECIPES_FIND, find)

    assert (tool.name, tool.description) == ("recipes_find", "Find recipes.")
    assert tool.target is find
    assert tool.output_model is find.output_model


def test_without_a_description_the_alias_keeps_the_one_of_its_tool() -> None:
    tool = AliasedTool(ToolAlias("recipes_find", "mongodb_find"), Find())

    assert tool.description == "Find documents in a collection."


def test_the_fixed_arguments_are_not_in_the_schema_the_caller_sees() -> None:
    schema = AliasedTool(RECIPES_FIND, Find()).input_model.model_json_schema()

    assert schema["title"] == "recipes_find_input"
    assert set(schema["properties"]) == {"filter", "limit"}
    assert "required" not in schema
    assert schema["properties"]["limit"] | {"title": None} == {
        "default": 10,
        "description": "Most documents to return.",
        "maximum": 50,
        "minimum": 1,
        "title": None,
        "type": "integer",
    }


async def test_a_call_sends_the_fixed_arguments_with_what_the_caller_gave() -> None:
    find = Find()
    tool = AliasedTool(RECIPES_FIND, find)

    output = await tool.run(tool.input_model.model_validate({"filter": {"vegan": True}}))

    assert output.model_dump() == {
        "received": {
            "database": "kitchen",
            "collection": "recipes",
            "filter": {"vegan": True},
            "limit": 10,
        }
    }


def test_the_caller_cannot_set_a_fixed_argument() -> None:
    tool = AliasedTool(RECIPES_FIND, Find())

    with pytest.raises(ValidationError, match="collection, database are fixed by 'recipes_find'"):
        tool.input_model.model_validate({"database": "billing", "collection": "invoices"})


async def test_through_the_invoker_a_fixed_argument_is_an_invalid_argument(logger) -> None:
    invoker = InvokeToolUseCase(ToolCatalog([AliasedTool(RECIPES_FIND, Find())]), logger)

    with pytest.raises(
        ToolFailure, match="Invalid arguments for 'recipes_find'.*database is fixed"
    ):
        await invoker.invoke("recipes_find", {"database": "billing"})


async def test_the_constraints_of_the_tool_still_apply_to_what_the_caller_gives(logger) -> None:
    invoker = InvokeToolUseCase(ToolCatalog([AliasedTool(RECIPES_FIND, Find())]), logger)

    with pytest.raises(ToolFailure, match="limit: Input should be less than or equal to 50"):
        await invoker.invoke("recipes_find", {"limit": 99})


async def test_a_call_the_tool_refuses_as_a_whole_is_a_tool_failure_naming_both() -> None:
    tool = AliasedTool(ToolAlias("recipes_dump", "mongodb_find", fixed=RECIPES_FIND.fixed), Find())

    with pytest.raises(
        ToolFailure, match="'recipes_dump' could not call 'mongodb_find'.*needs a filter"
    ):
        await tool.run(tool.input_model.model_validate({"limit": 30}))


async def test_each_call_gets_its_own_copy_of_the_fixed_arguments() -> None:
    find = Find()
    alias = ToolAlias(
        "vegan_find", "mongodb_find", fixed=RECIPES_FIND.fixed | {"filter": {"tags": ["vegan"]}}
    )
    tool = AliasedTool(alias, find)

    await tool.run(tool.input_model.model_validate({}))
    assert find.calls[0].filter is not None
    find.calls[0].filter["tags"].append("cheap")

    assert alias.fixed["filter"] == {"tags": ["vegan"]}


@pytest.mark.parametrize(
    ("fixed", "message"),
    [
        (
            {"database": "kitchen", "colection": "recipes"},
            "'mongodb_find' has no argument colection",
        ),
        (
            {"database": "kitchen", "limit": "many"},
            "don't fit 'mongodb_find': limit: Input should be a valid integer",
        ),
        ({"database": "kitchen", "limit": 500}, "limit: Input should be less than or equal to 50"),
    ],
)
def test_fixed_arguments_the_tool_would_refuse_are_refused_up_front(fixed, message) -> None:
    with pytest.raises(ValueError, match=f"alias 'recipes_find': .*{message}"):
        AliasedTool(ToolAlias("recipes_find", "mongodb_find", fixed=fixed), Find())


def test_a_fixed_value_the_tool_would_convert_is_accepted() -> None:
    tool = AliasedTool(ToolAlias("recipes_find", "mongodb_find", fixed={"limit": "20"}), Find())

    assert "limit" not in tool.input_model.model_fields


async def test_a_tool_that_takes_any_argument_can_be_given_any_fixed_one() -> None:
    tool = AliasedTool(ToolAlias("kitchen_issues", "jira_search", fixed={"project": "KIT"}), Open())

    output = await tool.run(tool.input_model.model_validate({"text": "oven"}))

    assert output.model_dump() == {"received": {"text": "oven", "project": "KIT"}}
    with pytest.raises(ValidationError, match="project is fixed by 'kitchen_issues'"):
        tool.input_model.model_validate({"project": "OPS"})


def test_a_tool_argument_named_like_the_alias_check_does_not_switch_the_check_off() -> None:
    class Shadowing(Find):
        input_model = create_model("shadowing_input", database=(str, ...), refuse_fixed=(str, ""))

    tool = AliasedTool(
        ToolAlias("recipes_find", "mongodb_find", fixed={"database": "kitchen"}), Shadowing()
    )

    with pytest.raises(ValidationError, match="database is fixed by 'recipes_find'"):
        tool.input_model.model_validate({"database": "billing", "refuse_fixed": "x"})

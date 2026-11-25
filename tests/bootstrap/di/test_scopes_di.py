import pytest
from pycraftcore.application_configuration.enum import ConnectorType, OperationType
from pycraftcore.application_configuration.model import McpConnector, McpOperation, McpTool
from pycraftcore.authentication.model.auth_type import AuthType
from pycraftcore.authentication.model.no_auth import NoAuth
from pycraftcore.mcp import RemoteTool

from agent_toolbox.adapter.outbound.mcp.mcp_backed_tool import McpBackedTool
from agent_toolbox.application.catalog.scoped_tool_catalog import ScopedToolCatalog
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.domain.model.tool_scope import ToolAlias, ToolScope
from bootstrap.di.scopes_di import ScopesDI, scope_from
from tests.agent_toolbox.stubs import Find


def scopes(make_di, logger, waits_for_its_server=lambda tool_name: False) -> ScopesDI:
    return ScopesDI(make_di()._configuration, logger, waits_for_its_server)


def test_the_scopes_come_from_the_operations_on_the_self_connector(make_di, logger) -> None:
    declared = {scope.name: scope for scope in scopes(make_di, logger).declared}

    assert list(declared) == [
        "all",
        "observation",
        "analysis",
        "coding",
        "security",
        "kitchen",
        "travel",
    ]
    assert declared["observation"].patterns == ("grafana_*",)
    assert declared["kitchen"].patterns == ("python_executor",)
    assert [alias.name for alias in declared["kitchen"].aliases] == [
        "recipes_find",
        "recipes_count",
        "recipe_versions_find",
        "recipe_versions_aggregate",
        "recipe_versions_schema",
        "ingredients_table",
    ]
    assert declared["kitchen"].alias("recipe_versions_find").fixed == {
        "connectionId": "preconfigured",
        "database": "kitchen",
        "collection": "recipe_versions",
    }


def test_a_scope_declared_twice_is_refused(make_di, logger) -> None:
    di = scopes(make_di, logger)
    observation = next(operation for operation in di.operations if operation.name == "observation")
    di.__dict__["operations"] = (*di.operations, observation)

    with pytest.raises(ValueError, match="declared twice: observation"):
        _ = di.declared


def mcp_operation(name: str, **values) -> McpOperation:
    return McpOperation(
        name=name,
        type=OperationType.mcp,
        connector=McpConnector(
            name="toolbox",
            type=ConnectorType.mcp,
            auth=NoAuth(type=AuthType.none),
            base_url="http://toolbox/mcp",
            timeout=30,
        ),
        **values,
    )


def test_a_scope_takes_its_patterns_and_its_wrapped_tools_from_the_operation() -> None:
    recipes = McpTool(
        name="recipes_find",
        tool="mongodb_find",
        description="Find recipes.",
        arguments={"database": "kitchen", "collection": "recipes"},
    )

    scope = scope_from(mcp_operation("kitchen", tools=["python_executor", recipes]))

    assert scope == ToolScope(
        "kitchen",
        ("python_executor",),
        (ToolAlias("recipes_find", "mongodb_find", "Find recipes.", recipes.arguments),),
    )


def test_a_wrapped_tool_sandbox_code_could_not_call_names_its_operation() -> None:
    operation = mcp_operation("kitchen", tools=[McpTool(name="recipes.find", tool="mongodb_find")])

    with pytest.raises(
        ValueError, match="operation 'kitchen' is not a valid scope: .*'recipes.find'"
    ):
        scope_from(operation)


def kitchen_tools(*aliases: ToolAlias, catalog: ToolCatalog | None = None) -> ScopedToolCatalog:
    return ScopedToolCatalog(catalog or ToolCatalog(), ToolScope("kitchen", (), aliases))


def test_an_alias_waiting_for_its_server_is_only_a_warning(make_di, logger) -> None:
    di = scopes(make_di, logger, waits_for_its_server=lambda tool_name: tool_name == "mongodb_find")

    di.check(kitchen_tools(ToolAlias("recipes_find", "mongodb_find")))

    assert logger.messages("warning") == [
        "Scope 'kitchen': alias 'recipes_find': its tool 'mongodb_find' is not in the catalog; "
        "it is published once its MCP server answers"
    ]


@pytest.mark.parametrize(
    ("alias", "message"),
    [
        (ToolAlias("recipes_find", "mongodb_fnd"), "its tool 'mongodb_fnd' is not in the catalog"),
        (ToolAlias("recipes_read", "file_readr"), "its tool 'file_readr' is not in the catalog"),
        (
            ToolAlias("recipes_find", "mongodb_find", fixed={"colection": "recipes"}),
            "'mongodb_find' has no argument colection",
        ),
    ],
)
def test_an_alias_that_cannot_be_built_while_its_server_answers_stops_the_boot(
    make_di, logger, alias, message
) -> None:
    di = scopes(make_di, logger)

    with pytest.raises(ValueError, match=f"scope 'kitchen': alias '{alias.name}': {message}"):
        di.check(kitchen_tools(alias, catalog=ToolCatalog([Find()])))


_MONGODB_COLLECTION: dict = {
    "connectionId": {"type": "string", "description": "Connection to use."},
    "database": {"type": "string", "description": "Database name."},
    "collection": {"type": "string", "description": "Collection name."},
}
_RESPONSE_LIMIT: dict = {
    "responseBytesLimit": {
        "type": "number",
        "default": 1048576,
        "description": "Most bytes of documents to return.",
    }
}
_MONGODB_REQUIRED: tuple[str, ...] = ("connectionId", "database", "collection")
REMOTE_SCHEMAS: dict[str, tuple[dict, tuple[str, ...]]] = {
    "mongodb_find": (
        _MONGODB_COLLECTION
        | {
            "filter": {
                "type": "object",
                "description": "Query filter, as for db.collection.find().",
            },
            "projection": {"type": "object", "description": "Fields to return or leave out."},
            "limit": {"type": "number", "default": 10, "description": "Most documents to return."},
            "sort": {
                "type": "object",
                "description": "Sort order: field to 1, -1, 'asc' or 'desc'.",
            },
        }
        | _RESPONSE_LIMIT,
        _MONGODB_REQUIRED,
    ),
    "mongodb_count": (
        _MONGODB_COLLECTION
        | {"query": {"type": "object", "description": "Filter of the documents to count."}},
        _MONGODB_REQUIRED,
    ),
    "mongodb_aggregate": (
        _MONGODB_COLLECTION
        | {"pipeline": {"type": "array", "description": "Aggregation pipeline stages."}}
        | _RESPONSE_LIMIT,
        (*_MONGODB_REQUIRED, "pipeline"),
    ),
    "mongodb_collection_schema": (
        _MONGODB_COLLECTION
        | {
            "sampleSize": {
                "type": "number",
                "default": 50,
                "description": "Documents sampled to infer the schema.",
            }
        }
        | _RESPONSE_LIMIT,
        _MONGODB_REQUIRED,
    ),
    "postgres_get_object_details": (
        {
            "schema_name": {"type": "string", "description": "Schema name."},
            "object_name": {"type": "string", "description": "Object name."},
            "object_type": {
                "type": "string",
                "default": "table",
                "description": "Object type: 'table', 'view', 'sequence', or 'extension'.",
            },
        },
        ("schema_name", "object_name"),
    ),
}


def remote_tool(name: str) -> McpBackedTool:
    properties, required = REMOTE_SCHEMAS[name]
    schema: dict = {"type": "object", "properties": properties, "required": list(required)}
    return McpBackedTool(None, RemoteTool(name, f"{name}.", schema), name)  # ty: ignore[invalid-argument-type]


def test_the_kitchen_scope_fits_the_real_servers_tools_and_hides_what_it_fixes(
    make_di, logger
) -> None:
    di = scopes(make_di, logger)
    kitchen: ToolScope = next(scope for scope in di.declared if scope.name == "kitchen")
    catalog = ToolCatalog([remote_tool(name) for name in REMOTE_SCHEMAS])

    tools = ScopedToolCatalog(catalog, kitchen)
    di.check(tools)

    assert [tool.name for tool in tools.tools] == [alias.name for alias in kitchen.aliases]
    assert set(tools.get("recipes_find").input_model.model_fields) == {
        "filter",
        "projection",
        "limit",
        "sort",
        "responseBytesLimit",
    }
    assert set(tools.get("ingredients_table").input_model.model_fields) == set()

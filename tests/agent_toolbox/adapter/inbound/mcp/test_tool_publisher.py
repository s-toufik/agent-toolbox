from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from agent_toolbox.adapter.inbound.mcp.tool_publisher import McpToolPublisher
from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from agent_toolbox.application.catalog.scoped_tool_catalog import ScopedToolCatalog
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.model.tool_scope import ToolAlias, ToolScope
from tests.agent_toolbox.stubs import Find, Named, RecordingToolServer, StubSandbox


def listed(server: RecordingToolServer) -> dict[str, str]:
    return {name: tool.description for name, tool in server.tools.items()}


async def test_published_changes_reach_tools_list_and_python_executor_s_description(
    logger,
) -> None:
    catalog = ToolCatalog()
    catalog.add(
        ExecutePython(
            StubSandbox(),
            allowed_modules=(),
            timeout_seconds=10,
            callable_tools=lambda: [
                tool.name for tool in catalog.tools if tool.name != "python_executor"
            ],
        )
    )
    catalog.add(Named("file_reader"))
    server = RecordingToolServer()
    binder = ToolBinder(InvokeToolUseCase(catalog, logger))
    binder.bind(server)
    publisher = McpToolPublisher(server, binder, catalog, refreshed=("python_executor",))

    publisher.publish(catalog.replace("grafana", [Named("grafana_search")]))
    after_add = listed(server)
    publisher.publish(catalog.replace("grafana", []))
    after_remove = listed(server)

    assert set(after_add) == {"python_executor", "file_reader", "grafana_search"}
    assert "Tools callable in code: file_reader, grafana_search." in after_add["python_executor"]
    assert set(after_remove) == {"python_executor", "file_reader"}
    assert "grafana_search" not in after_remove["python_executor"]


async def test_a_published_tool_runs_through_the_use_case(logger) -> None:
    catalog = ToolCatalog()
    server = RecordingToolServer()
    binder = ToolBinder(InvokeToolUseCase(catalog, logger))
    publisher = McpToolPublisher(server, binder, catalog)

    publisher.publish(catalog.replace("grafana", [Named("grafana_search")]))
    result = await server.call("grafana_search", {"text": "hi"})

    assert result == {"echoed": "grafana_search:hi"}


async def test_a_scope_s_publisher_binds_only_the_scope_s_tools(logger) -> None:
    catalog = ToolCatalog()
    scope = ToolScope("observation", ("grafana_*",))
    view = ScopedToolCatalog(catalog, scope)
    server = RecordingToolServer()
    binder = ToolBinder(InvokeToolUseCase(view, logger))
    publisher = McpToolPublisher(server, binder, view, scope=scope)

    publisher.publish(catalog.replace("mcp", [Named("grafana_search"), Named("postgres_sql")]))

    assert set(listed(server)) == {"grafana_search"}


RECIPES_FIND = ToolAlias(
    "recipes_find", "mongodb_find", fixed={"database": "kitchen", "collection": "recipes"}
)


def kitchen_server(logger, *aliases: ToolAlias):
    catalog = ToolCatalog()
    scope = ToolScope("kitchen", (), aliases)
    view = ScopedToolCatalog(catalog, scope)
    server = RecordingToolServer()
    binder = ToolBinder(InvokeToolUseCase(view, logger))
    binder.bind(server)
    return catalog, server, McpToolPublisher(server, binder, view, scope=scope)


def schemas(server: RecordingToolServer) -> dict[str, set[str]]:
    return {name: set(tool.input_model.model_fields) for name, tool in server.tools.items()}


async def test_an_alias_is_published_when_its_tool_arrives_and_withdrawn_when_it_leaves(
    logger,
) -> None:
    catalog, server, publisher = kitchen_server(logger, RECIPES_FIND)

    before = schemas(server)
    publisher.publish(catalog.replace("mongodb", [Find()]))
    arrived = schemas(server)
    result = await server.call("recipes_find", {"limit": 5})
    publisher.publish(catalog.replace("mongodb", []))

    assert before == {}
    assert arrived == {"recipes_find": {"filter", "limit"}}
    assert result["received"] == {
        "database": "kitchen",
        "collection": "recipes",
        "filter": None,
        "limit": 5,
    }
    assert schemas(server) == {}


async def test_an_alias_follows_the_schema_of_its_tool(logger) -> None:
    catalog, server, publisher = kitchen_server(logger, ToolAlias("search", "mongodb_find"))

    publisher.publish(catalog.replace("mongodb", [Named("mongodb_find")]))
    first = schemas(server)
    publisher.publish(catalog.replace("mongodb", [Find()]))

    assert first == {"search": {"text", "times"}}
    assert schemas(server) == {"search": {"database", "collection", "filter", "limit"}}


async def test_a_lock_that_no_longer_fits_its_tool_is_withdrawn_without_exposing_the_tool(
    logger,
) -> None:
    locked = ToolAlias("mongodb_find", "mongodb_find", fixed={"times": 2})
    catalog, server, publisher = kitchen_server(logger, locked)

    publisher.publish(catalog.replace("mongodb", [Named("mongodb_find")]))
    locked_schema = schemas(server)
    publisher.publish(catalog.replace("mongodb", [Find()]))

    assert locked_schema == {"mongodb_find": {"text"}}
    assert schemas(server) == {}

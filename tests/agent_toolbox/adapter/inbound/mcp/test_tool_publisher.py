from agent_toolbox.adapter.inbound.mcp.mcp_server_factory import build_mcp_server
from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from agent_toolbox.adapter.inbound.mcp.tool_publisher import McpToolPublisher
from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from tests.agent_toolbox.stubs import Named, StubSandbox


async def listed(server) -> dict[str, str]:
    return {tool.name: tool.description or "" for tool in await server.list_tools()}


async def test_published_changes_reach_tools_list_and_python_executor_s_description(
    logger,
) -> None:
    catalog = ToolCatalog()
    data = catalog.without("python_executor")
    catalog.add(
        ExecutePython(
            StubSandbox(),
            allowed_modules=(),
            timeout_seconds=10,
            signatures=lambda: [f"{tool.name}()" for tool in data.tools],
        )
    )
    catalog.add(Named("file_reader"))
    server = build_mcp_server(name="toolbox", version="1.0.0")
    binder = ToolBinder(InvokeToolUseCase(catalog, logger))
    binder.bind(server)
    publisher = McpToolPublisher(server, binder, catalog, refreshed=("python_executor",))

    publisher.publish(catalog.replace("grafana", [Named("grafana_search")]))
    after_add = await listed(server)
    publisher.publish(catalog.replace("grafana", []))
    after_remove = await listed(server)

    assert set(after_add) == {"python_executor", "file_reader", "grafana_search"}
    assert "grafana_search()" in after_add["python_executor"]
    assert set(after_remove) == {"python_executor", "file_reader"}
    assert "grafana_search()" not in after_remove["python_executor"]


async def test_a_published_tool_runs_through_the_use_case(logger) -> None:
    catalog = ToolCatalog()
    server = build_mcp_server(name="toolbox", version="1.0.0")
    binder = ToolBinder(InvokeToolUseCase(catalog, logger))
    publisher = McpToolPublisher(server, binder, catalog)

    publisher.publish(catalog.replace("grafana", [Named("grafana_search")]))
    result = await server.call_tool("grafana_search", {"text": "hi"})

    assert "grafana_search:hi" in str(result)

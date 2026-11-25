import pytest
from pycraftcore.application_configuration.enum import ConnectorType, OperationType
from pycraftcore.application_configuration.model import (
    McpConnector,
    McpOperation,
    McpRefresh,
    McpTool,
)
from pycraftcore.authentication.model.auth_type import AuthType
from pycraftcore.authentication.model.no_auth import NoAuth


def test_external_mcp_servers_without_a_url_are_skipped(make_di, without_external_mcp) -> None:
    external = make_di()._external_mcp

    assert set(external.connectors) == {
        "external_mcp_grafana",
        "external_mcp_mongodb",
        "external_mcp_postgres",
    }
    assert external.sources == []
    assert external.operations["external_mcp_mongodb"].prefix == "mongodb"
    assert "self" not in external.operations


def test_external_mcp_servers_take_their_refresh_pace_from_the_configuration(
    make_di, monkeypatch
) -> None:
    monkeypatch.setenv("GRAFANA_MCP_URL", "http://grafana-mcp:8000/mcp")
    monkeypatch.setenv("MCP_REFRESH_INTERVAL", "120")
    monkeypatch.setenv("MCP_RETRY_DELAY", "2")

    [grafana] = make_di()._external_mcp.sources

    assert grafana.name == "grafana"
    assert grafana.policy == McpRefresh(interval=120, retry_delay=2, max_retry_delay=60)


def test_an_external_operation_that_wraps_tools_is_refused(make_di, monkeypatch) -> None:
    monkeypatch.setenv("MONGODB_MCP_URL", "http://mongodb-mcp:8000/mcp")
    external = make_di()._external_mcp
    external.__dict__["operations"] = {
        "external_mcp_mongodb": McpOperation(
            name="external_mcp_mongodb",
            type=OperationType.mcp,
            connector=McpConnector(
                name="external_mcp_mongodb",
                type=ConnectorType.mcp,
                auth=NoAuth(type=AuthType.none),
                base_url="http://mongodb-mcp:8000/mcp",
                timeout=30,
            ),
            tools=[McpTool(name="recipes_find", tool="find")],
        )
    }

    with pytest.raises(
        ValueError, match="'external_mcp_mongodb' wraps tools: wrap them in a scope"
    ):
        _ = external.sources


def test_a_tool_waits_for_its_server_only_while_that_server_is_down_or_unset(make_di) -> None:
    external = make_di()._external_mcp
    external.health.down("mongodb", "connection refused")
    external.health.up("postgres")

    assert external.waits_for_its_server("mongodb_find")
    assert external.waits_for_its_server("grafana_search_dashboards")
    assert not external.waits_for_its_server("postgres_execute_sql")
    assert not external.waits_for_its_server("file_reader")

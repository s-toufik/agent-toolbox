import asyncio
from pathlib import Path
from typing import Any

import pytest
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pycraftcore.file_handler.adapter import Handler
from pycraftcore.query_language.adapter import SqlHandlerFactory
from pycraftcore.runtime.adapter import PythonSafeCodeFactory
from pycraftcore.runtime.schema import SafeCodeSettings

from agent_toolbox.adapter.inbound.mcp.tool_binder import ToolBinder
from agent_toolbox.adapter.inbound.sandbox.tool_bridge import SandboxToolBridge
from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from agent_toolbox.adapter.outbound.file.reader_tool import ReadFile
from agent_toolbox.adapter.outbound.file.writer_tool import WriteFile
from agent_toolbox.adapter.outbound.sandbox.python_sandbox import PythonSandbox
from agent_toolbox.adapter.outbound.sql.sql_tool import QueryUsers
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.model.working_directory import WorkingDirectory
from tests.agent_toolbox.stubs import StubRepository

_SANDBOX_CALL = """
try:
    result = {{"ok": True, "value": {name}(**{arguments!r})}}
except ToolError as error:
    result = {{"ok": False, "error": str(error)}}
"""


@pytest.fixture
def files(tmp_path: Path) -> Path:
    (tmp_path / "data.json").write_text('{"name": "ada", "tags": ["a", "b"]}')
    (tmp_path / "rows.csv").write_text("id,name\n1,ada\n2,bob\n")
    (tmp_path / "notes.md").write_text("# Title\n\nline 2\nline 3\n")
    return tmp_path


def _server(logger, working_directory: Path | None = None) -> MCPServer:
    toolbox_working_directory = (
        WorkingDirectory(str(working_directory)) if working_directory else None
    )
    data_tools: list[Tool] = [
        QueryUsers(StubRepository(rows=[{"id": 1, "name": "ada"}]), SqlHandlerFactory()),
        ReadFile(Handler, toolbox_working_directory),
        WriteFile(Handler, toolbox_working_directory),
    ]
    bridge = SandboxToolBridge(InvokeToolUseCase(data_tools, logger))
    settings = SafeCodeSettings(
        code_timeout=10, working_directory=str(working_directory) if working_directory else None
    )
    sandbox = PythonSandbox(PythonSafeCodeFactory(settings), asyncio.Semaphore(4), bridge.server)
    python = ExecutePython(sandbox, allowed_modules=(), timeout_seconds=10)

    mcp = MCPServer(name="parity")
    ToolBinder(InvokeToolUseCase([python, *data_tools], logger)).bind(mcp)
    return mcp


@pytest.fixture
def server(logger) -> MCPServer:
    return _server(logger)


@pytest.fixture
def working_directory_server(logger, files: Path) -> MCPServer:
    return _server(logger, working_directory=files)


async def _direct(server: MCPServer, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        result = await server.call_tool(name, arguments)
    except ToolError as error:
        return {"ok": False, "error": str(error)}
    return {"ok": True, "value": result.structured_content}


async def _in_sandbox(server: MCPServer, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    code = _SANDBOX_CALL.format(name=name, arguments=arguments)
    result = await server.call_tool("python_executor", {"code": code})
    outcome: dict[str, Any] = result.structured_content["result"]
    if not outcome["ok"]:
        # MCP prefixes every tool error with the tool name; the tool's own message follows.
        outcome["error"] = f"Error executing tool {name}: {outcome['error']}"
    return outcome


CASES: list[tuple[str, str, dict[str, Any]]] = [
    ("read json", "file_reader", {"file_path": "{dir}/data.json"}),
    ("read csv", "file_reader", {"file_path": "{dir}/rows.csv"}),
    ("read markdown", "file_reader", {"file_path": "{dir}/notes.md"}),
    ("read lines", "file_reader", {"file_path": "{dir}/notes.md", "start": 2, "count": 2}),
    ("read missing file", "file_reader", {"file_path": "{dir}/missing.md"}),
    ("write json", "file_writer", {"file_path": "{dir}/out.json", "data": {"a": [1, 2]}}),
    ("write markdown", "file_writer", {"file_path": "{dir}/out.md", "data": "# Out"}),
    ("write to missing dir", "file_writer", {"file_path": "{dir}/no/out.md", "data": "x"}),
    ("query", "users_tables", {"query": "SELECT id, name FROM users"}),
    ("forbidden query", "users_tables", {"query": "DROP TABLE users"}),
]


@pytest.mark.parametrize(("case", "name", "arguments"), CASES, ids=[case[0] for case in CASES])
async def test_direct_and_sandboxed_calls_return_the_same_thing(
    server: MCPServer, files: Path, case: str, name: str, arguments: dict[str, Any]
) -> None:
    arguments = {
        key: value.format(dir=files) if isinstance(value, str) else value
        for key, value in arguments.items()
    }

    direct = await _direct(server, name, arguments)
    sandboxed = await _in_sandbox(server, name, arguments)

    assert sandboxed == direct


async def test_invalid_arguments_are_rejected_on_both_paths(server: MCPServer) -> None:
    # Both validate against the same input model; only MCP's wording of the error differs.
    direct = await _direct(server, "file_reader", {"start": "x"})
    sandboxed = await _in_sandbox(server, "file_reader", {"start": "x"})

    assert direct["ok"] is False and sandboxed["ok"] is False
    assert "file_path" in direct["error"] and "file_path" in sandboxed["error"]


WORKING_DIRECTORY_CASES: list[tuple[str, str, dict[str, Any]]] = [
    ("read relative", "file_reader", {"file_path": "data.json"}),
    ("read absolute inside", "file_reader", {"file_path": "{dir}/rows.csv"}),
    ("read outside", "file_reader", {"file_path": "../outside.md"}),
    ("write relative", "file_writer", {"file_path": "out.md", "data": "# Out"}),
    ("write outside", "file_writer", {"file_path": "/tmp/escaped.md", "data": "x"}),
]


@pytest.mark.parametrize(
    ("case", "name", "arguments"),
    WORKING_DIRECTORY_CASES,
    ids=[case[0] for case in WORKING_DIRECTORY_CASES],
)
async def test_with_a_working_directory_direct_and_sandboxed_calls_return_the_same_thing(
    working_directory_server: MCPServer,
    files: Path,
    case: str,
    name: str,
    arguments: dict[str, Any],
) -> None:
    arguments = {
        key: value.format(dir=files) if isinstance(value, str) else value
        for key, value in arguments.items()
    }

    assert await _in_sandbox(working_directory_server, name, arguments) == await _direct(
        working_directory_server, name, arguments
    )


async def test_with_a_working_directory_a_relative_path_is_the_same_file_in_code_and_in_tools(
    working_directory_server: MCPServer,
) -> None:
    code = (
        'written = file_writer(file_path="shared.md", data="# Shared")\n'
        'result = {"path": written["path"], "text": open("shared.md").read()}\n'
    )

    result = await working_directory_server.call_tool("python_executor", {"code": code})

    assert result.structured_content["result"]["text"] == "# Shared"

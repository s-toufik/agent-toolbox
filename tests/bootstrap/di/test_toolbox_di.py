from pathlib import Path

from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from bootstrap.configuration.settings import ProcessSettings
from bootstrap.di.toolbox_di import ToolboxDI

REAL_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
TOOL_NAMES = {"users_tables", "python_executor", "file_reader", "file_writer"}


def make_di(sandbox_tool_access: bool = False, working_directory: Path | None = None) -> ToolboxDI:
    return ToolboxDI(
        ProcessSettings(
            role="toolbox",
            environment="debug",
            configuration_directory=REAL_CONFIG_DIR,
            working_directory=working_directory,
            sandbox_tool_access=sandbox_tool_access,
        )
    )


def _set_required_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("USER_DB_HOST", str(tmp_path))
    monkeypatch.setenv("USER_DB_NAME", "users")
    monkeypatch.setenv("CHECKPOINT_DB_HOST", str(tmp_path))
    monkeypatch.setenv("CHECKPOINT_DB_NAME", "checkpoint")


async def test_use_case_serves_every_tool_and_connects_the_sqlite_repository(
    tmp_path, monkeypatch
) -> None:
    _set_required_env(monkeypatch, tmp_path)
    di = make_di()

    use_case = await di._invoke_tool_use_case()

    assert {tool.name for tool in use_case.tools} == TOOL_NAMES
    assert len(di._repositories) == 1
    assert await use_case.invoke("python_executor", {"code": "result = 1 + 1"}) == {
        "result_type": "int",
        "result": 2,
        "stdout": "",
    }

    await di._stop_factories()


def test_python_tool_has_no_tool_functions_without_sandbox_tool_access(tmp_path) -> None:
    tool: ExecutePython = make_di()._execute_python([])

    assert "ToolError" not in tool.description


async def test_python_tool_lists_the_data_tools_with_sandbox_tool_access(
    tmp_path, monkeypatch
) -> None:
    _set_required_env(monkeypatch, tmp_path)
    di = make_di(sandbox_tool_access=True, working_directory=tmp_path)

    [python] = [
        tool for tool in (await di._invoke_tool_use_case()).tools if tool.name == "python_executor"
    ]

    assert "file_reader(*, file_path: str" in python.description
    assert "users_tables(*, query: str, dialect: str = 'sqlite') -> {rows:" in python.description
    assert f"Working directory: {tmp_path}." in python.description

    await di._stop_factories()

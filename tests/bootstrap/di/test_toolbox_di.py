from pathlib import Path

from bootstrap.configuration.settings import ProcessSettings
from bootstrap.di.toolbox_di import ToolboxDI

REAL_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


def make_di(tmp_path: Path) -> ToolboxDI:
    return ToolboxDI(
        ProcessSettings(
            role="toolbox",
            environment="debug",
            configuration_directory=REAL_CONFIG_DIR,
            host="0.0.0.0",
            port=8001,
        )
    )


def _set_required_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("USER_DB_HOST", str(tmp_path))
    monkeypatch.setenv("USER_DB_NAME", "users")
    monkeypatch.setenv("CHECKPOINT_DB_HOST", str(tmp_path))
    monkeypatch.setenv("CHECKPOINT_DB_NAME", "checkpoint")


def test_python_tool_is_wired_to_the_python_executor_specification(tmp_path, monkeypatch) -> None:
    _set_required_env(monkeypatch, tmp_path)
    di = make_di(tmp_path)

    tool = di._python_tool()

    assert tool.specification.name == "python_executor"


async def test_sql_tool_connects_a_real_sqlite_repository(tmp_path, monkeypatch) -> None:
    _set_required_env(monkeypatch, tmp_path)
    di = make_di(tmp_path)

    tool = await di._sql_tool()

    assert tool.specification.name == "users_tables"
    assert len(di._repositories) == 1

    await di._stop_factories()


async def test_tools_returns_both_the_sql_and_python_tools(tmp_path, monkeypatch) -> None:
    _set_required_env(monkeypatch, tmp_path)
    di = make_di(tmp_path)

    tools = await di._tools()

    assert {tool.specification.name for tool in tools} == {
        "users_tables",
        "python_executor",
        "file_reader",
        "file_writer",
    }

    await di._stop_factories()


def test_file_reader_tool_is_wired_to_the_file_reader_specification(tmp_path, monkeypatch) -> None:
    _set_required_env(monkeypatch, tmp_path)
    di = make_di(tmp_path)

    tool = di._file_reader_tool()

    assert tool.specification.name == "file_reader"


def test_file_writer_tool_is_wired_to_the_file_writer_specification(tmp_path, monkeypatch) -> None:
    _set_required_env(monkeypatch, tmp_path)
    di = make_di(tmp_path)

    tool = di._file_writer_tool()

    assert tool.specification.name == "file_writer"


async def test_tool_registry_exposes_both_tools_by_name(tmp_path, monkeypatch) -> None:
    _set_required_env(monkeypatch, tmp_path)
    di = make_di(tmp_path)

    registry = await di._tool_registry()

    assert set(registry.names()) == {
        "users_tables",
        "python_executor",
        "file_reader",
        "file_writer",
    }

    await di._stop_factories()


async def test_execute_tool_use_case_is_wired_to_the_given_registry(tmp_path, monkeypatch) -> None:
    _set_required_env(monkeypatch, tmp_path)
    di = make_di(tmp_path)
    registry = await di._tool_registry()

    use_case = di._execute_tool_use_case(registry)

    from agent_toolbox.domain.model.tool_invocation import ToolInvocation

    outcome = await use_case.execute(
        ToolInvocation(id="1", name="python_executor", arguments={"code": "result = 1 + 1"})
    )
    assert not outcome.failed

    await di._stop_factories()

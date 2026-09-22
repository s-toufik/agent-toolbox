from pathlib import Path

from agent_toolbox.adapter.outbound.file.model.file_read_result import FileReadResult
from agent_toolbox.adapter.outbound.file.model.file_write_result import FileWriteResult
from agent_toolbox.adapter.outbound.specification import file_reader, file_writer, user_database
from bootstrap.configuration.settings import ProcessSettings
from bootstrap.di.toolbox_di import ToolboxDI, _shape, _tool_signature

REAL_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


def test_shape_lists_the_fields_of_a_plain_model() -> None:
    assert _shape(FileWriteResult) == "{path}"


def test_shape_lists_each_variant_of_a_discriminated_union_by_its_tag() -> None:
    shape = _shape(FileReadResult)

    assert "format='text': {format, path, text}" in shape
    assert "format='structured': {format, path, data}" in shape
    assert "format='rows': {format, path, rows}" in shape
    assert "format='lines': {format, path, lines}" in shape


def test_tool_signature_shows_arguments_and_the_output_shape() -> None:
    assert _tool_signature(file_writer.SPECIFICATION) == "file_writer(file_path, data) -> {path}"
    assert (
        _tool_signature(user_database.SPECIFICATION)
        == "users_tables(query, dialect=None) -> {rows}"
    )


def test_tool_signature_shows_the_file_reader_shape_hint_before_any_code_runs() -> None:
    signature = _tool_signature(file_reader.SPECIFICATION)

    assert signature.startswith("file_reader(file_path, start=None, count=None) -> ")
    assert "format='structured': {format, path, data}" in signature


def make_di(tmp_path: Path) -> ToolboxDI:
    return ToolboxDI(
        ProcessSettings(
            role="toolbox",
            environment="debug",
            configuration_directory=REAL_CONFIG_DIR,
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

    tool = di._python_tool([])

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

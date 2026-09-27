import pytest

from agent_toolbox.adapter.outbound.file.model.file_write_input import WriteFileInput
from agent_toolbox.adapter.outbound.file.model.file_write_output import WriteFileOutput
from agent_toolbox.adapter.outbound.file.writer_tool import WriteFile
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.vault import Vault
from tests.agent_toolbox.stubs import StubFileHandler, file_handler_provider


async def _write(handler: StubFileHandler, **arguments) -> WriteFileOutput:
    return await WriteFile(file_handler_provider(handler)).run(WriteFileInput(**arguments))


@pytest.mark.parametrize(
    ("file_path", "data"),
    [
        ("/f.json", {"a": 1}),
        ("/f.csv", [{"a": 1}, {"a": 2}]),
        ("/f.md", "# Title"),
    ],
)
async def test_data_is_written_as_given(file_path, data) -> None:
    handler = StubFileHandler()

    output = await _write(handler, file_path=file_path, data=data)

    assert handler.written == data
    assert output == WriteFileOutput(path=file_path)


async def test_structured_formats_also_accept_a_json_string() -> None:
    handler = StubFileHandler()

    await _write(handler, file_path="/f.yml", data='{"a": 1}')

    assert handler.written == {"a": 1}


async def test_invalid_json_string_for_a_structured_format_is_rejected() -> None:
    with pytest.raises(ToolFailure, match="Invalid JSON in data"):
        await _write(StubFileHandler(), file_path="/f.json", data="{nope")


async def test_text_formats_keep_a_json_looking_string_as_text() -> None:
    handler = StubFileHandler()

    await _write(handler, file_path="/f.txt", data='{"a": 1}')

    assert handler.written == '{"a": 1}'


async def test_empty_file_path_is_rejected() -> None:
    with pytest.raises(ToolFailure, match="No file_path provided."):
        await _write(StubFileHandler(), file_path="", data="x")


async def test_missing_directory_is_reported() -> None:
    handler = StubFileHandler(write_error=FileNotFoundError("x"))

    with pytest.raises(ToolFailure, match="File path not found."):
        await _write(handler, file_path="/missing/f.md", data="x")


async def test_with_a_vault_relative_paths_resolve_inside_it(tmp_path) -> None:
    handler = StubFileHandler()
    tool = WriteFile(file_handler_provider(handler), Vault(str(tmp_path)))

    output = await tool.run(WriteFileInput(file_path="report.md", data="# R"))

    assert output == WriteFileOutput(path=str(tmp_path.resolve() / "report.md"))


async def test_with_a_vault_paths_outside_it_are_never_written(tmp_path) -> None:
    handler = StubFileHandler()
    tool = WriteFile(file_handler_provider(handler), Vault(str(tmp_path)))

    with pytest.raises(ToolFailure, match="is outside the vault."):
        await tool.run(WriteFileInput(file_path="../escaped.md", data="x"))

    assert handler.written is None

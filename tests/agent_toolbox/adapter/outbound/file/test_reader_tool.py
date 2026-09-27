import pytest
from pycraftcore.file_handler.enum.read_chunk_mode import ReadChunkMode

from agent_toolbox.adapter.outbound.file.model.file_read_input import ReadFileInput
from agent_toolbox.adapter.outbound.file.model.file_read_output import (
    LinesContent,
    RowsContent,
    StructuredContent,
    TextContent,
)
from agent_toolbox.adapter.outbound.file.reader_tool import ReadFile
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.vault import Vault
from tests.agent_toolbox.stubs import StubFileHandler, file_handler_provider


async def _read(handler: StubFileHandler, **arguments):
    return await ReadFile(file_handler_provider(handler)).run(ReadFileInput(**arguments))


@pytest.mark.parametrize(
    ("data", "content"),
    [
        ("# Title", TextContent(text="# Title")),
        ({"a": 1}, StructuredContent(data={"a": 1})),
        ([1, 2], StructuredContent(data=[1, 2])),
        ([{"a": "1"}], RowsContent(rows=[{"a": "1"}])),
    ],
)
async def test_whole_file_content_is_shaped_by_what_was_parsed(data, content) -> None:
    output = await _read(StubFileHandler(read_result=data), file_path="/f")

    assert output.path == "/f"
    assert output.content == content


async def test_start_or_count_reads_lines() -> None:
    handler = StubFileHandler(read_result=["a\n", "b\n"])

    output = await _read(handler, file_path="/f.txt", start=1, count=2)

    assert handler.read_with == (ReadChunkMode.LINE, 1, 2)
    assert output.content == LinesContent(lines=["a\n", "b\n"])


async def test_empty_file_path_is_rejected() -> None:
    with pytest.raises(ToolFailure, match="No file_path provided."):
        await _read(StubFileHandler(), file_path="  ")


async def test_missing_file_is_reported() -> None:
    with pytest.raises(ToolFailure, match="File not found."):
        await _read(StubFileHandler(read_error=FileNotFoundError("x")), file_path="/f")


async def test_other_read_errors_keep_their_message() -> None:
    with pytest.raises(ToolFailure, match="unsupported extension"):
        await _read(StubFileHandler(read_error=ValueError("unsupported extension")), file_path="/f")


async def test_with_a_vault_relative_paths_resolve_inside_it(tmp_path) -> None:
    handler = StubFileHandler(read_result="x")
    tool = ReadFile(file_handler_provider(handler), Vault(str(tmp_path)))

    output = await tool.run(ReadFileInput(file_path="notes.md"))

    assert output.path == str(tmp_path.resolve() / "notes.md")
    assert str(tmp_path) in tool.description


async def test_with_a_vault_paths_outside_it_are_refused(tmp_path) -> None:
    handler = StubFileHandler(read_result="x")
    tool = ReadFile(file_handler_provider(handler), Vault(str(tmp_path)))

    with pytest.raises(ToolFailure, match="'/etc/hosts' is outside the vault."):
        await tool.run(ReadFileInput(file_path="/etc/hosts"))

    assert handler.read_with is None

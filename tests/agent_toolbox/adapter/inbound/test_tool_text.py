from pycraftcore.file_handler.adapter import Handler

from agent_toolbox.adapter.inbound.tool_text import (
    LONGEST_SUMMARY,
    call_signature,
    described,
    python_stub,
    return_shape,
    summary,
)
from agent_toolbox.adapter.outbound.file.model.file_read_output import ReadFileOutput
from agent_toolbox.adapter.outbound.file.reader_tool import ReadFile
from agent_toolbox.adapter.outbound.file.writer_tool import WriteFile
from agent_toolbox.adapter.outbound.sql.model.sql_query_output import QueryUsersOutput
from tests.agent_toolbox.stubs import Echo


def test_call_signature_shows_types_and_defaults() -> None:
    assert call_signature(Echo()) == "echo(*, text: str, times: int = 1)"
    assert call_signature(ReadFile(Handler)) == (
        "file_reader(*, file_path: str, start: int | None = None, count: int | None = None)"
    )


def test_return_shape_of_a_plain_model() -> None:
    assert return_shape(QueryUsersOutput) == "{rows: list[dict[str, Any]]}"


def test_return_shape_spells_out_each_variant_of_a_discriminated_field() -> None:
    assert return_shape(ReadFileOutput) == (
        "{path: str, content: {format: 'text', text: str}"
        " | {format: 'structured', data: dict[str, Any] | list[Any]}"
        " | {format: 'rows', rows: list[dict[str, Any]]}"
        " | {format: 'lines', lines: list[str]}}"
    )


def test_python_stub_is_the_signature_then_the_first_sentence_of_the_description() -> None:
    lines = python_stub(WriteFile(Handler)).splitlines()

    assert lines[0] == (
        "file_writer(*, file_path: str, data: dict[str, Any] | list[dict[str, Any]] | str)"
        " -> {path: str}"
    )
    assert lines[1] == f"    {summary(WriteFile(Handler).description)}"
    assert len(lines) == 2


def test_python_stub_of_a_tool_with_a_one_sentence_description() -> None:
    assert (
        python_stub(Echo())
        == "echo(*, text: str, times: int = 1) -> {echoed: str}\n    Repeat text."
    )


def test_summary_keeps_the_first_sentence_and_cuts_a_long_one() -> None:
    assert summary("Query logs. Then much more.") == "Query logs."
    assert summary("Query\n  logs from Loki.") == "Query logs from Loki."
    long = summary("word " * 100)
    assert len(long) <= LONGEST_SUMMARY
    assert long.endswith("…")


def test_described_appends_the_return_shape_to_the_description() -> None:
    assert described(Echo()) == "Repeat text.\n\nReturns: {echoed: str}"

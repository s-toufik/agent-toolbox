from agent_toolbox.adapter.inbound.tool_text import described, return_shape
from agent_toolbox.adapter.outbound.file.model.file_read_output import ReadFileOutput
from agent_toolbox.adapter.outbound.sql.model.sql_query_output import QueryUsersOutput
from tests.agent_toolbox.stubs import Echo


def test_return_shape_of_a_plain_model() -> None:
    assert return_shape(QueryUsersOutput) == "{rows: list[dict[str, Any]]}"


def test_return_shape_spells_out_each_variant_of_a_discriminated_field() -> None:
    assert return_shape(ReadFileOutput) == (
        "{path: str, content: {format: 'text', text: str}"
        " | {format: 'structured', data: dict[str, Any] | list[Any]}"
        " | {format: 'rows', rows: list[dict[str, Any]]}"
        " | {format: 'lines', lines: list[str]}}"
    )


def test_described_appends_the_return_shape_to_the_description() -> None:
    assert described(Echo()) == "Repeat text.\n\nReturns: {echoed: str}"

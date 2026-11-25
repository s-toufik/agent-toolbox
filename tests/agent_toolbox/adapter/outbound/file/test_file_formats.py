import datetime
import decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pycraftcore.file_handler.adapter import Handler

from agent_toolbox.adapter.outbound.file.reader_tool import ReadFile
from agent_toolbox.adapter.outbound.file.writer_tool import WriteFile
from agent_toolbox.domain.exception.tool_failure import ToolFailure

ROWS = [{"name": "tomato", "kcal": 18}, {"name": "oat", "kcal": 389}]


async def read(path, **arguments) -> dict:
    tool = ReadFile(Handler)
    output = await tool.run(tool.input_model(file_path=str(path), **arguments))
    return output.model_dump(mode="json")["content"]


async def write(path, data) -> None:
    tool = WriteFile(Handler)
    await tool.run(tool.input_model(file_path=str(path), data=data))


@pytest.mark.parametrize("name", ["recipes.xlsx", "recipes.parquet", "recipes.csv"])
async def test_rows_written_to_a_table_file_are_read_back_as_rows(tmp_path, name) -> None:
    await write(tmp_path / name, ROWS)

    content = await read(tmp_path / name)

    assert content["format"] == "rows"
    assert [row["name"] for row in content["rows"]] == ["tomato", "oat"]


async def test_a_table_file_also_takes_its_rows_as_a_json_string(tmp_path) -> None:
    await write(tmp_path / "recipes.xlsx", '[{"name": "tomato"}]')

    assert (await read(tmp_path / "recipes.xlsx"))["rows"] == [{"name": "tomato"}]


async def test_dates_decimals_and_binary_cells_come_back_as_json_values(tmp_path) -> None:
    table = pa.table(
        {
            "day": [datetime.date(2026, 1, 2)],
            "price": pa.array([decimal.Decimal("1.20")], pa.decimal128(5, 2)),
            "raw": [b"\xff\x00"],
        }
    )
    pq.write_table(table, tmp_path / "prices.parquet")

    content = await read(tmp_path / "prices.parquet")

    assert content["rows"] == [{"day": "2026-01-02", "price": "1.20", "raw": "_wA="}]


async def test_a_csv_with_semicolons_is_read_as_rows(tmp_path) -> None:
    (tmp_path / "recipes.csv").write_text("name;kcal\ntomato;18\n", encoding="utf-8")

    assert (await read(tmp_path / "recipes.csv"))["rows"] == [{"name": "tomato", "kcal": "18"}]


@pytest.mark.parametrize("name", ["recipes.xlsx", "recipes.parquet", "recipes.xls"])
async def test_a_binary_file_is_not_read_by_lines(tmp_path, name) -> None:
    with pytest.raises(ToolFailure, match=r"start and count read lines of a text file; a \.\w+"):
        await read(tmp_path / name, start=0, count=5)


@pytest.mark.parametrize("name", ["recipes.csv", "recipes.xlsx", "recipes.parquet"])
async def test_a_table_file_refuses_anything_but_rows(tmp_path, name) -> None:
    with pytest.raises(ToolFailure, match="takes a list of row objects"):
        await write(tmp_path / name, {"name": "tomato"})
    assert not (tmp_path / name).exists()


async def test_a_legacy_xls_file_is_read_only(tmp_path) -> None:
    with pytest.raises(ToolFailure, match=r"isn't supported; write \.xlsx instead"):
        await write(tmp_path / "recipes.xls", ROWS)


def test_the_descriptions_list_every_format_each_tool_handles() -> None:
    for name in ("json", "csv", "xlsx", "xls", "parquet", "md", "svg"):
        assert name in ReadFile.description
    assert "xlsx, parquet" in WriteFile.description
    assert ".xls files can be read, not written" in WriteFile.description

import re

import pytest

from agent_toolbox.adapter.outbound.code.python_tool_description import (
    LEAD_ALONE,
    LEAD_WITH_TOOLS,
    PythonToolDescription,
)

SHOWN_IN_CATALOGS: int = 160


@pytest.mark.parametrize("lead", [LEAD_WITH_TOOLS, LEAD_ALONE])
def test_the_lead_is_one_short_sentence_so_tool_catalogs_show_it_whole(lead: str) -> None:
    assert len(lead) <= SHOWN_IN_CATALOGS
    assert re.split(r"(?<=[.!?])\s", lead) == [lead]


def test_with_callable_tools_it_says_how_to_call_them_and_names_them() -> None:
    text = PythonToolDescription(
        ("json", "pandas"), 900, callable_tools=("file_reader", "echo")
    ).render()

    assert text.startswith(f"{LEAD_WITH_TOOLS}\n- Call a tool as a function")
    assert "raises ToolError" in text
    assert "one direct call with a small limit" in text
    assert "json.loads(df.to_json(orient='records', date_format='iso'))" in text
    assert "Timeout: 900 seconds." in text
    assert "Modules: json, pandas." in text
    assert text.endswith("Tools callable in code: file_reader, echo.")


def test_without_callable_tools_it_says_nothing_about_calling_tools() -> None:
    text = PythonToolDescription(("math",), 30).render()

    assert text.startswith(f"{LEAD_ALONE}\n- Use it for heavy work")
    assert "ToolError" not in text
    assert "Tools callable in code" not in text
    assert "WORKING_DIRECTORY" not in text
    assert text.endswith("Modules: math.")


def test_the_working_directory_line_names_the_directory_and_its_variable() -> None:
    text = PythonToolDescription(("math",), 30, working_directory="/work").render()

    assert (
        "- Files: /work is the code's current directory, also in WORKING_DIRECTORY. Use relative "
        "paths: the file tools resolve them the same way. Access outside it is denied."
    ) in text

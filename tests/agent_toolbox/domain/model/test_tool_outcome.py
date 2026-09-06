from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome

INVOCATION = ToolInvocation(id="1", name="t", arguments={"a": 1})


def test_argument_returns_the_default_when_missing() -> None:
    assert INVOCATION.argument("missing", "fallback") == "fallback"
    assert INVOCATION.argument("a") == 1


def test_success_outcome_content_is_just_the_output() -> None:
    outcome = ToolOutcome.success(INVOCATION, "rows")

    assert outcome.failed is False
    assert outcome.content == "rows"


def test_failure_with_no_output_shows_only_the_error() -> None:
    outcome = ToolOutcome.failure(INVOCATION, "boom")

    assert outcome.failed is True
    assert outcome.content == "Error: boom"


def test_failure_with_partial_output_keeps_both() -> None:
    outcome = ToolOutcome.failure(INVOCATION, "boom", output="partial")

    assert outcome.content == "partial\nError: boom"

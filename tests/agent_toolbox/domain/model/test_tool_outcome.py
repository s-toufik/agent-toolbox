from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome

INVOCATION = ToolInvocation(id="1", name="t", arguments={"a": 1})


def test_argument_returns_the_default_when_missing() -> None:
    assert INVOCATION.argument("missing", "fallback") == "fallback"
    assert INVOCATION.argument("a") == 1


def test_success_outcome_carries_the_typed_output_and_no_error() -> None:
    outcome = ToolOutcome.success(INVOCATION, "rows")

    assert outcome.failed is False
    assert outcome.output == "rows"
    assert outcome.error is None


def test_failure_outcome_carries_the_error_and_no_output() -> None:
    outcome = ToolOutcome.failure(INVOCATION, "boom")

    assert outcome.failed is True
    assert outcome.output is None
    assert outcome.error == "boom"

from agent_toolbox.domain.exception.tool_execution_exeception import ToolExecutionException
from agent_toolbox.domain.exception.unknown_tool_exeception import UnknownToolException


def test_both_domain_exceptions_are_plain_exceptions() -> None:
    assert isinstance(ToolExecutionException("boom"), Exception)
    assert isinstance(UnknownToolException("missing"), Exception)

import pytest

from agent_toolbox.adapter.outbound.registry.in_memory_tool_registry import InMemoryToolRegistry
from agent_toolbox.application.use_case.execute_tool_usecase import ExecuteToolUseCase
from agent_toolbox.domain.enum.parameter_type import ParameterType
from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome
from agent_toolbox.domain.model.tool_specification import ToolParameter, ToolSpecification

SPECIFICATION = ToolSpecification(
    name="echo",
    description="Echo the input.",
    parameters=(ToolParameter(name="value", type=ParameterType.STRING, description="Anything."),),
)


class EchoTool:
    @property
    def specification(self) -> ToolSpecification:
        return SPECIFICATION

    async def invoke(self, invocation: ToolInvocation) -> ToolOutcome:
        return ToolOutcome.success(invocation, invocation.argument("value", ""))


class ExplodingTool:
    @property
    def specification(self) -> ToolSpecification:
        return ToolSpecification(name="boom", description="Always fails.")

    async def invoke(self, invocation: ToolInvocation) -> ToolOutcome:
        raise RuntimeError("kaboom")


@pytest.fixture
def use_case(logger) -> ExecuteToolUseCase:
    registry = InMemoryToolRegistry([EchoTool(), ExplodingTool()])
    return ExecuteToolUseCase(registry, logger)


async def test_returns_the_tool_output(use_case: ExecuteToolUseCase) -> None:
    outcome = await use_case.execute(
        ToolInvocation(id="1", name="echo", arguments={"value": "hello"})
    )
    assert outcome.output == "hello"
    assert not outcome.failed


async def test_unknown_tool_becomes_a_failed_outcome(use_case: ExecuteToolUseCase) -> None:
    outcome = await use_case.execute(ToolInvocation(id="2", name="nope"))
    assert outcome.failed
    assert "nope" in (outcome.error or "")


async def test_raising_tool_is_contained(use_case: ExecuteToolUseCase) -> None:
    outcome = await use_case.execute(ToolInvocation(id="3", name="boom"))
    assert outcome.failed
    assert "kaboom" in (outcome.error or "")

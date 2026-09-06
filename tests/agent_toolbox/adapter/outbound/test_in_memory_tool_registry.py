import pytest

from agent_toolbox.adapter.outbound.registry.in_memory_tool_registry import InMemoryToolRegistry
from agent_toolbox.domain.exception.unknown_tool_exeception import UnknownToolException
from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome
from agent_toolbox.domain.model.tool_specification import ToolSpecification


class StubTool:
    def __init__(self, name: str) -> None:
        self._specification = ToolSpecification(name=name, description=f"{name}.")

    @property
    def specification(self) -> ToolSpecification:
        return self._specification

    async def invoke(self, invocation: ToolInvocation) -> ToolOutcome:
        raise AssertionError("not expected to be called")


def test_get_returns_the_matching_tool() -> None:
    registry = InMemoryToolRegistry([StubTool("a"), StubTool("b")])

    assert registry.get("a").specification.name == "a"


def test_get_raises_for_an_unknown_name() -> None:
    registry = InMemoryToolRegistry([StubTool("a")])

    with pytest.raises(UnknownToolException):
        registry.get("missing")


def test_specifications_lists_every_registered_tool() -> None:
    registry = InMemoryToolRegistry([StubTool("a"), StubTool("b")])

    names = {spec.name for spec in registry.specifications()}

    assert names == {"a", "b"}


def test_names_and_len() -> None:
    registry = InMemoryToolRegistry([StubTool("a"), StubTool("b")])

    assert set(registry.names()) == {"a", "b"}
    assert len(registry) == 2

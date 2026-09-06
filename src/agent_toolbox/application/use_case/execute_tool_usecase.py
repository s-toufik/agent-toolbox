import traceback

from pycraftcore.logger.port import Logger

from agent_toolbox.application.port.outbound.tool_port import ToolPort, ToolRegistryPort
from agent_toolbox.domain.exception.unknown_tool_exeception import UnknownToolException
from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome


class ExecuteToolUseCase:
    def __init__(self, registry: ToolRegistryPort, logger: Logger) -> None:
        self._registry = registry
        self._logger = logger

    async def execute(self, invocation: ToolInvocation) -> ToolOutcome:
        self._logger.info(f"[{invocation.id}] tool '{invocation.name}' invoked")

        try:
            tool: ToolPort = self._registry.get(invocation.name)
        except UnknownToolException as exception:
            self._logger.warning(f"[{invocation.id}] {exception}")
            return ToolOutcome.failure(invocation, str(exception))

        try:
            outcome: ToolOutcome = await tool.invoke(invocation)
        except Exception as exception:
            traceback_str: str = "".join(traceback.format_exception(exception))
            self._logger.error(
                f"[{invocation.id}] tool '{invocation.name}' raised:\n{traceback_str}"
            )
            return ToolOutcome.failure(invocation, f"Tool execution failed: {exception}")

        if outcome.failed:
            self._logger.warning(f"[{invocation.id}] tool '{invocation.name}': {outcome.error}")

        return outcome

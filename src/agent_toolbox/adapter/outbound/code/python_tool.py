import asyncio
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from pycraftcore.runtime import Code, CodeFactory
from pycraftcore.runtime.schema import CodeStdout
from pycraftcore.runtime.schema.host_bridge import HostBridgeConfig

from agent_toolbox.adapter.outbound.code.model.python_execution_result import (
    PythonExecutionResult,
)
from agent_toolbox.adapter.outbound.code.tool_bridge import ToolBridgeServer
from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome
from agent_toolbox.domain.model.tool_specification import ToolSpecification


class PythonTool:
    def __init__(
        self,
        code_factory: CodeFactory,
        specification: ToolSpecification,
        semaphore: asyncio.Semaphore,
        bridge_server_factory: Callable[[], ToolBridgeServer] | None = None,
    ) -> None:
        self._code_factory: CodeFactory = code_factory
        self._specification: ToolSpecification = specification
        self._semaphore: asyncio.Semaphore = semaphore
        self._bridge_server_factory: Callable[[], ToolBridgeServer] | None = bridge_server_factory

    @property
    def specification(self) -> ToolSpecification:
        return self._specification

    async def invoke(self, invocation: ToolInvocation) -> ToolOutcome[PythonExecutionResult]:
        code: str = invocation.arguments.get("code", "") or ""

        if not code.strip():
            return ToolOutcome.failure(invocation, "No code provided.")

        async with self._bridge() as host_bridge:
            executor: Code = self._code_factory(
                code=code,
                code_template=None,
                host_bridge=host_bridge,
            )

            async with self._semaphore:
                result: CodeStdout = await executor.execute()

        if result.stderr:
            return ToolOutcome.failure(invocation, result.stderr)

        parsed: dict = json.loads(result.stdout)
        return ToolOutcome.success(
            invocation,
            PythonExecutionResult(result_type=parsed["__type__"], result=parsed["result"]),
        )

    @asynccontextmanager
    async def _bridge(self) -> AsyncIterator[HostBridgeConfig | None]:
        if self._bridge_server_factory is None:
            yield None
            return

        async with self._bridge_server_factory() as server:
            yield HostBridgeConfig(
                host=server.host,
                port=server.port,
                token=server.token,
                function_names=server.tool_names,
            )

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from pycraftcore.runtime import Code, CodeFactory
from pycraftcore.runtime.adapter import HostBridgeServer
from pycraftcore.runtime.schema import CodeResult, CodeStdout, HostBridgeConfig

from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.sandbox_run import SandboxRun


class PythonSandbox:
    def __init__(
        self,
        code_factory: CodeFactory,
        semaphore: asyncio.Semaphore,
        bridge_server: Callable[[], HostBridgeServer] | None = None,
    ) -> None:
        self._code_factory = code_factory
        self._semaphore = semaphore
        self._bridge_server = bridge_server

    async def run(self, code: str) -> SandboxRun:
        async with self._bridge() as host_bridge:
            executor: Code = self._code_factory(code=code, host_bridge=host_bridge)

            async with self._semaphore:
                output: CodeStdout = await executor.execute()

        # The runner prints its result envelope only when the code succeeded; anything
        # else on stderr alongside it (warnings) doesn't make the run a failure.
        try:
            result: CodeResult = CodeResult.from_stdout(output.stdout)
        except ValueError, KeyError, TypeError:
            raise ToolFailure(output.stderr or "The sandbox returned no result.") from None

        return SandboxRun(type_name=result.type_name, value=result.value, printed=result.printed)

    @asynccontextmanager
    async def _bridge(self) -> AsyncIterator[HostBridgeConfig | None]:
        if self._bridge_server is None:
            yield None
            return

        async with self._bridge_server() as server:
            yield server.config

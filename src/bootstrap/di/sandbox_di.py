import asyncio

from pycraftcore.logger.port import Logger
from pycraftcore.runtime.adapter import PythonSafeCodeFactory
from pycraftcore.runtime.adapter.python.python_runner_template import PYTHON_ALLOWLIST
from pycraftcore.runtime.schema import SafeCodeSettings

from agent_toolbox.adapter.inbound.sandbox.tool_bridge import SandboxToolBridge
from agent_toolbox.adapter.inbound.tool_text import python_stub
from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from agent_toolbox.adapter.outbound.sandbox.python_sandbox import PythonSandbox
from agent_toolbox.application.port.outbound.tool_lookup_port import ToolLookup
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.model.working_directory import WorkingDirectory

SANDBOX_TIMEOUT_SECONDS: int = 900
SANDBOX_MAX_MEMORY_MB: int = 256
# Each scope gets a sandbox so overall concurrency is limited by the number of scopes times the max sandbox concurrency
SANDBOX_MAX_CONCURRENCY: int = 8


class SandboxDI:
    def __init__(
        self, logger: Logger, working_directory: WorkingDirectory | None, tool_access: bool
    ) -> None:
        self._logger = logger
        self._working_directory = working_directory
        self._tool_access = tool_access

    def execute_python(self, lookup: ToolLookup) -> ExecutePython:
        root: str | None = self._working_directory.root if self._working_directory else None

        bridge: SandboxToolBridge | None = None
        if self._tool_access:
            bridge = SandboxToolBridge(InvokeToolUseCase(lookup, self._logger))

        settings = SafeCodeSettings(
            code_timeout=SANDBOX_TIMEOUT_SECONDS,
            max_memory_mb=SANDBOX_MAX_MEMORY_MB,
            working_directory=root,
        )
        sandbox = PythonSandbox(
            code_factory=PythonSafeCodeFactory(settings=settings),
            semaphore=asyncio.Semaphore(SANDBOX_MAX_CONCURRENCY),
            bridge_server=bridge.server if bridge else None,
        )
        return ExecutePython(
            sandbox,
            allowed_modules=PYTHON_ALLOWLIST,
            timeout_seconds=SANDBOX_TIMEOUT_SECONDS,
            working_directory=root,
            signatures=(lambda: [python_stub(tool) for tool in lookup.tools]) if bridge else tuple,
        )

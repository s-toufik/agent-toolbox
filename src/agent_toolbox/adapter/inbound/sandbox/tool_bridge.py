import uuid
from typing import Any

from pycraftcore.http.context.request_context import request_id_context
from pycraftcore.runtime.adapter import HostBridgeServer

from agent_toolbox.application.port.inbound.invoke_tool_port import InvokeToolPort


class SandboxToolBridge:
    def __init__(
        self, invoker: InvokeToolPort, max_calls: int = 200, call_timeout: float = 30.0
    ) -> None:
        self._invoker = invoker
        self._max_calls = max_calls
        self._call_timeout = call_timeout

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(tool.name for tool in self._invoker.tools)

    def server(self) -> HostBridgeServer:
        invoker = self._invoker
        invocation_id = f"sandbox_{request_id_context.get() or uuid.uuid4().hex[:8]}"

        async def handle(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            return await invoker.invoke(name, arguments, invocation_id)

        return HostBridgeServer(
            handle, self.tool_names, max_calls=self._max_calls, call_timeout=self._call_timeout
        )

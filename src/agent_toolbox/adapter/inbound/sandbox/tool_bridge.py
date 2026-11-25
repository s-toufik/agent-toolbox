from typing import Any

from pycraftcore.context.request_id_context import request_id_context
from pycraftcore.runtime.adapter import HostBridgeServer

from agent_toolbox.application.port.inbound.invoke_tool_port import InvokeToolPort

MAX_CALLS: int = 200
CALL_TIMEOUT_SECONDS: float = 30.0


class SandboxToolBridge:
    def __init__(self, invoker: InvokeToolPort) -> None:
        self._invoker = invoker

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(tool.name for tool in self._invoker.tools)

    def server(self) -> HostBridgeServer:
        invoker = self._invoker
        request_id = request_id_context.get()

        async def handle(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            token = request_id_context.set(request_id)
            try:
                return await invoker.invoke(name, arguments)
            finally:
                request_id_context.reset(token)

        return HostBridgeServer(
            handle, self.tool_names, max_calls=MAX_CALLS, call_timeout=CALL_TIMEOUT_SECONDS
        )

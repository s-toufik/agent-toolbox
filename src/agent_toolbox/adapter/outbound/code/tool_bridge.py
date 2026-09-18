import asyncio
import json
import uuid
from typing import TYPE_CHECKING, Any

from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome

if TYPE_CHECKING:
    from agent_toolbox.application.use_case.execute_tool_usecase import ExecuteToolUseCase


class ToolBridgeServer:
    def __init__(
        self,
        use_case: ExecuteToolUseCase,
        tool_names: tuple[str, ...],
        token: str,
        tool_defaults: dict[str, dict[str, Any]] | None = None,
        max_calls: int = 200,
        call_timeout: float = 30.0,
        context_id: str | None = None,
    ) -> None:
        self._use_case: ExecuteToolUseCase = use_case
        self._tool_names: tuple[str, ...] = tuple(tool_names)
        self._token: str = token
        self._tool_defaults: dict[str, dict[str, Any]] = dict(tool_defaults or {})
        self._max_calls: int = max_calls
        self._call_timeout: float = call_timeout
        self._server: asyncio.AbstractServer | None = None
        self._host = "127.0.0.1"
        self._port = 0
        self._context_id = (
            f"sandbox_{context_id}" if context_id else f"sandbox_{uuid.uuid4().hex[:8]}"
        )

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def token(self) -> str:
        return self._token

    @property
    def tool_names(self) -> tuple[str, ...]:
        return self._tool_names

    async def __aenter__(self) -> ToolBridgeServer:
        self._server = await asyncio.start_server(
            self._handle,
            self._host,
            self._port,
        )

        sock = self._server.sockets[0]
        self._port = sock.getsockname()[1]

        return self

    async def __aexit__(
        self,
        *_: object,
    ) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        calls = 0

        try:
            while line := await reader.readline():
                calls += 1
                over_quota: bool = calls > self._max_calls

                response: dict[str, str | None] = (
                    {
                        "output": "",
                        "error": "Tool call quota exceeded.",
                    }
                    if over_quota
                    else await self._respond(line)
                )

                writer.write(json.dumps(response).encode("utf-8") + b"\n")
                await writer.drain()

                if over_quota:
                    break

        except ConnectionError, asyncio.CancelledError:
            pass

        finally:
            writer.close()

    async def _respond(
        self,
        line: bytes,
    ) -> dict[str, str | None]:
        try:
            request: Any = json.loads(line)
        except json.JSONDecodeError:
            return {
                "output": "",
                "error": "Malformed request.",
            }

        if request.get("token") != self._token:
            return {
                "output": "",
                "error": "Unauthorized.",
            }

        name: Any = request.get("tool")

        if name not in self._tool_names:
            return {
                "output": "",
                "error": f"Tool {name!r} is not available in the sandbox.",
            }

        merged: dict[str, Any] = {
            **self._tool_defaults.get(name, {}),
            **(request.get("arguments") or {}),
        }

        arguments: dict[str, Any] = {
            key: value for key, value in merged.items() if value is not None
        }

        invocation = ToolInvocation(
            id=self._context_id,
            name=name,
            arguments=arguments,
        )

        try:
            outcome: ToolOutcome = await asyncio.wait_for(
                self._use_case.execute(invocation),
                self._call_timeout,
            )
        except TimeoutError:
            return {
                "output": "",
                "error": "Tool call timed out.",
            }

        return {
            "output": outcome.output,
            "error": outcome.error,
        }

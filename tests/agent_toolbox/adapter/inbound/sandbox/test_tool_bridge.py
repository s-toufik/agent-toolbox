import asyncio
import json
from collections.abc import Mapping
from typing import Any

from pycraftcore.context.request_id_context import request_id_context

from agent_toolbox.adapter.inbound.sandbox.tool_bridge import SandboxToolBridge
from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from tests.agent_toolbox.stubs import Echo


async def _call(bridge: SandboxToolBridge, function: str, **arguments: Any) -> dict[str, Any]:
    async with bridge.server() as server:
        config = server.config
        reader, writer = await asyncio.open_connection(config.host, config.port)
        request = {"token": config.token, "function": function, "arguments": arguments}
        writer.write(json.dumps(request).encode("utf-8") + b"\n")
        await writer.drain()
        response = json.loads(await reader.readline())
        writer.close()
    return response


def test_serves_every_tool_of_its_invoker(logger) -> None:
    assert SandboxToolBridge(InvokeToolUseCase([Echo()], logger)).tool_names == ("echo",)


async def test_returns_what_the_invoker_returns(logger) -> None:
    bridge = SandboxToolBridge(InvokeToolUseCase([Echo()], logger))

    response = await _call(bridge, "echo", text="ab", times=2)

    assert response == {"ok": True, "output": {"echoed": "abab"}}


async def test_returns_the_tool_failure_message(logger) -> None:
    bridge = SandboxToolBridge(
        InvokeToolUseCase([Echo(error=ToolFailure("File not found."))], logger)
    )

    response = await _call(bridge, "echo", text="a")

    assert response == {"ok": False, "error": "File not found."}


async def test_calls_run_under_the_request_id_of_the_run_that_started_the_sandbox(logger) -> None:
    seen: list[str | None] = []

    class Recorder(InvokeToolUseCase):
        async def invoke(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
            seen.append(request_id_context.get())
            return await super().invoke(name, arguments)

    bridge = SandboxToolBridge(Recorder([Echo()], logger))
    token = request_id_context.set("req-1")
    try:
        server = bridge.server()
    finally:
        request_id_context.reset(token)

    async with server:
        config = server.config
        reader, writer = await asyncio.open_connection(config.host, config.port)
        request = {"token": config.token, "function": "echo", "arguments": {"text": "a"}}
        writer.write(json.dumps(request).encode("utf-8") + b"\n")
        await writer.drain()
        await reader.readline()
        writer.close()

    assert seen == ["req-1"]
    assert logger.messages("info") == ["tool 'echo' invoked"]

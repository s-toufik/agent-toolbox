import asyncio
import json
from typing import Any

from pycraftcore.http.context.request_context import request_id_context

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


async def test_calls_are_logged_under_the_request_id(logger) -> None:
    bridge = SandboxToolBridge(InvokeToolUseCase([Echo()], logger))
    token = request_id_context.set("req-1")
    try:
        await _call(bridge, "echo", text="a")
    finally:
        request_id_context.reset(token)

    assert logger.messages("info") == ["[sandbox_req-1] tool 'echo' invoked"]

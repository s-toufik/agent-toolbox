from types import SimpleNamespace
from typing import cast

from mcp import Client
from mcp.server.context import ServerRequestContext
from opentelemetry import trace

from agent_toolbox.adapter.inbound.mcp.mcp_server_factory import build_mcp_server
from agent_toolbox.adapter.inbound.mcp.request_spans import RequestSpans


def _server():
    server = build_mcp_server(name="toolbox", version="1.0.0")

    @server.tool()
    def add(a: int, b: int) -> int:
        return a + b

    return server


class RecordingSpans:
    def __init__(self) -> None:
        self.methods: list[str] = []

    async def __call__(self, ctx, call_next):
        self.methods.append(ctx.method)
        return await call_next(ctx)


async def _through(middleware: RequestSpans, method: str) -> str:
    async def handler(ctx):
        return {"handled": ctx.method}

    result = await middleware(cast(ServerRequestContext, SimpleNamespace(method=method)), handler)
    return cast(dict, result)["handled"]


async def test_requests_get_a_span_and_notifications_are_passed_straight_on() -> None:
    spans = RecordingSpans()
    middleware = RequestSpans(spans)

    handled = [await _through(middleware, m) for m in ("tools/call", "notifications/initialized")]

    assert handled == ["tools/call", "notifications/initialized"]
    assert spans.methods == ["tools/call"]


def test_the_server_wraps_the_sdk_s_span_middleware() -> None:
    assert any(isinstance(m, RequestSpans) for m in _server().middleware)


async def test_a_call_joins_the_caller_s_trace(spans) -> None:
    with trace.get_tracer("test").start_as_current_span("agent run_tools") as caller:
        async with Client(_server()) as client:
            await client.call_tool("add", {"a": 1, "b": 2})

    [call] = [span for span in spans.get_finished_spans() if span.name == "tools/call add"]
    assert call.context is not None
    assert call.context.trace_id == caller.get_span_context().trace_id

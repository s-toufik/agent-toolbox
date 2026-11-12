from typing import Any

from mcp.server.context import CallNext, HandlerResult, ServerMiddleware, ServerRequestContext

NOTIFICATION_PREFIX = "notifications/"


class RequestSpans:
    def __init__(self, spans: ServerMiddleware[Any]) -> None:
        self._spans = spans

    async def __call__(
        self, ctx: ServerRequestContext[Any, Any], call_next: CallNext
    ) -> HandlerResult:
        if ctx.method.startswith(NOTIFICATION_PREFIX):
            return await call_next(ctx)
        return await self._spans(ctx, call_next)

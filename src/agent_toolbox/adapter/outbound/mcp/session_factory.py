import base64
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

import httpx2
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._stream_protocols import ReadStream, WriteStream
from mcp.shared.message import SessionMessage
from pycraftcore.application_configuration.model.connector import McpConnector
from pycraftcore.application_configuration.model.operation import McpOperation
from pycraftcore.authentication import AuthTyping, BasicAuth, TokenAuth
from pycraftcore.context import request_id_context


class McpSessionFactory:
    def __init__(self, connector: McpConnector, operation: McpOperation | None = None) -> None:
        self._connector = connector
        self._operation = operation

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[ClientSession]:
        async with AsyncExitStack() as stack:
            read, write = await self._open_transport(stack)
            session: ClientSession = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            yield session

    async def _open_transport(
        self, stack: AsyncExitStack
    ) -> tuple[ReadStream[SessionMessage | Exception], WriteStream[SessionMessage]] | Any:
        headers: dict[str, str] = self._headers()

        if self._connector.transport == "sse":
            return await stack.enter_async_context(
                sse_client(
                    self._connector.base_url,
                    headers=headers,
                    timeout=self._connector.timeout,
                )
            )

        http_client: httpx2.AsyncClient = httpx2.AsyncClient(
            headers=headers,
            timeout=httpx2.Timeout(self._connector.timeout),
            follow_redirects=True,
            trust_env=False,
        )
        await stack.enter_async_context(http_client)
        return await stack.enter_async_context(
            streamable_http_client(self._connector.base_url, http_client=http_client)
        )

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = self._operation_headers()
        request_id: str | None = request_id_context.get()
        if request_id:
            headers["X-Request-ID"] = request_id

        auth: AuthTyping = self._connector.auth
        if isinstance(auth, TokenAuth):
            headers[auth.key_name] = auth.key_value
        elif isinstance(auth, BasicAuth):
            token = base64.b64encode(f"{auth.username}:{auth.password}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        return headers

    def _operation_headers(self) -> dict[str, str]:
        if self._operation is None:
            return {}
        headers: dict[str, Any] = self._operation.parameters.get("header") or {}
        return {key: str(value) for key, value in headers.items() if value}

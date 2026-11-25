import re
from collections.abc import Collection

from pycraftcore.mcp import McpClient

from agent_toolbox.adapter.outbound.mcp.mcp_backed_tool import McpBackedTool
from agent_toolbox.application.port.outbound.tool_port import Tool

_NOT_IDENTIFIER = re.compile(r"[^0-9A-Za-z_]")


def published_name(prefix: str, remote_name: str) -> str:
    safe: str = _NOT_IDENTIFIER.sub("_", remote_name)
    return f"{prefix}_{safe}" if prefix else safe


class McpToolProvider:
    def __init__(
        self, client: McpClient, prefix: str = "", allowed: Collection[str] | None = None
    ) -> None:
        self._client = client
        self._prefix = prefix
        self._allowed: frozenset[str] | None = frozenset(allowed) if allowed else None

    async def tools(self) -> list[Tool]:
        return [
            McpBackedTool(self._client, remote, published_name(self._prefix, remote.name))
            for remote in await self._client.list_tools()
            if self._allowed is None or remote.name in self._allowed
        ]

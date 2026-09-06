import asyncio
from typing import Any

from pycraftcore.file_handler.port import FileHandlerFactory, FileHandlerProvider

from agent_toolbox.domain.model.tool_invocation import ToolInvocation
from agent_toolbox.domain.model.tool_outcome import ToolOutcome
from agent_toolbox.domain.model.tool_specification import ToolSpecification


class FileReaderTool:
    def __init__(
        self,
        file_handler_provider: FileHandlerProvider,
        specification: ToolSpecification,
    ) -> None:
        self._file_handler_factory = file_handler_provider
        self._specification = specification

    @property
    def specification(self) -> ToolSpecification:
        return self._specification

    async def invoke(self, invocation: ToolInvocation) -> ToolOutcome:
        file_path: str = invocation.argument("file_path", "") or ""

        if not file_path.strip():
            return ToolOutcome.failure(invocation, "No file_path provided.")

        executor: FileHandlerFactory = self._file_handler_factory(file_path=file_path)

        try:
            result: dict[str, Any] = await asyncio.to_thread(executor.read)
        except FileNotFoundError:
            return ToolOutcome.failure(invocation, "File not found.")
        except Exception as exception:
            return ToolOutcome.failure(invocation, str(exception))

        return ToolOutcome.success(invocation, str(result))

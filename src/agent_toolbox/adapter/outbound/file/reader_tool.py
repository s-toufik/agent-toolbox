import asyncio
import sys
from typing import Any

from pycraftcore.file_handler.enum.read_chunk_mode import ReadChunkMode
from pycraftcore.file_handler.port import FileHandlerFactory, FileHandlerProvider

from agent_toolbox.adapter.outbound.file.model.file_read_input import ReadFileInput
from agent_toolbox.adapter.outbound.file.model.file_read_output import (
    LinesContent,
    ReadFileOutput,
    RowsContent,
    StructuredContent,
    TextContent,
)
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.working_directory import WorkingDirectory


class ReadFile(Tool[ReadFileInput, ReadFileOutput]):
    name = "file_reader"
    description = (
        "Read a file and return its contents. Supported formats: yml, yaml, json, csv, md, txt, svg. "
        f"Current system: {sys.platform}."
    )
    input_model = ReadFileInput
    output_model = ReadFileOutput

    def __init__(
        self,
        file_handler_provider: FileHandlerProvider,
        working_directory: WorkingDirectory | None = None,
    ) -> None:
        self._file_handler_provider = file_handler_provider
        self._working_directory = working_directory
        if working_directory is not None:
            self.description = (
                f"{self.description} Files are read from the working directory: "
                f"{working_directory.root}."
            )

    async def run(self, arguments: ReadFileInput) -> ReadFileOutput:
        if not arguments.file_path.strip():
            raise ToolFailure("No file_path provided.")

        path: str = (
            self._working_directory.resolve(arguments.file_path)
            if self._working_directory
            else arguments.file_path
        )
        in_lines: bool = arguments.start is not None or arguments.count is not None
        handler: FileHandlerFactory = self._file_handler_provider(file_path=path)

        try:
            data: Any = await asyncio.to_thread(
                handler.read,
                ReadChunkMode.LINE if in_lines else None,
                arguments.start,
                arguments.count,
            )
        except FileNotFoundError as error:
            raise ToolFailure("File not found.") from error
        except Exception as error:
            raise ToolFailure(str(error)) from error

        return ReadFileOutput(path=path, content=_content(data, in_lines))


def _content(
    data: Any, in_lines: bool
) -> TextContent | StructuredContent | RowsContent | LinesContent:
    if in_lines:
        return LinesContent(lines=data)
    if isinstance(data, str):
        return TextContent(text=data)
    if isinstance(data, list) and all(isinstance(row, dict) for row in data):
        return RowsContent(rows=data)
    return StructuredContent(data=data)

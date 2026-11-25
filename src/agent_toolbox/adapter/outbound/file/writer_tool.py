import asyncio
import sys
from typing import Any

import orjson
from pycraftcore.file_handler.port import FileHandlerFactory, FileHandlerProvider

from agent_toolbox.adapter.outbound.file.file_format import (
    DOCUMENT_FORMATS,
    READ_ONLY_FORMATS,
    TABLE_FORMATS,
    TEXT_FORMATS,
    extension,
    listed,
)
from agent_toolbox.adapter.outbound.file.model.file_write_input import WriteFileInput
from agent_toolbox.adapter.outbound.file.model.file_write_output import WriteFileOutput
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.working_directory import WorkingDirectory


class WriteFile(Tool[WriteFileInput, WriteFileOutput]):
    name = "file_writer"
    description = (
        "Write data to a file, replacing its contents: an object for "
        f"{listed(DOCUMENT_FORMATS)}; a list of row objects for "
        f"{listed(TABLE_FORMATS, READ_ONLY_FORMATS)}; a string for {listed(TEXT_FORMATS)}. "
        f".{', .'.join(sorted(READ_ONLY_FORMATS))} files can be read, not written. "
        f"Current system: {sys.platform}."
    )
    input_model = WriteFileInput
    output_model = WriteFileOutput

    def __init__(
        self,
        file_handler_provider: FileHandlerProvider,
        working_directory: WorkingDirectory | None = None,
    ) -> None:
        self._file_handler_provider = file_handler_provider
        self._working_directory = working_directory
        if working_directory is not None:
            self.description = (
                f"{self.description} Files are written to the working directory: "
                f"{working_directory.root}."
            )

    async def run(self, arguments: WriteFileInput) -> WriteFileOutput:
        if not arguments.file_path.strip():
            raise ToolFailure("No file_path provided.")

        path: str = (
            self._working_directory.resolve(arguments.file_path)
            if self._working_directory
            else arguments.file_path
        )
        data: Any = _decoded(path, arguments.data)
        if extension(path) in TABLE_FORMATS and not _is_rows(data):
            raise ToolFailure(
                f"A .{extension(path)} file takes a list of row objects, one per row."
            )
        handler: FileHandlerFactory = self._file_handler_provider(file_path=path)

        try:
            await asyncio.to_thread(handler.write, data)
        except FileNotFoundError as error:
            raise ToolFailure("File path not found.") from error
        except Exception as error:
            raise ToolFailure(str(error)) from error

        return WriteFileOutput(path=path)


def _decoded(file_path: str, data: Any) -> Any:
    # Structured formats also accept their data as a JSON string.
    if not isinstance(data, str) or extension(file_path) in TEXT_FORMATS:
        return data

    try:
        return orjson.loads(data)
    except orjson.JSONDecodeError as error:
        raise ToolFailure(f"Invalid JSON in data: {error}") from error


def _is_rows(data: Any) -> bool:
    return isinstance(data, list) and all(isinstance(row, dict) for row in data)

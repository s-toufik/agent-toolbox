import asyncio
import sys
from pathlib import PurePath
from typing import Any

import orjson
from pycraftcore.file_handler.port import FileHandlerFactory, FileHandlerProvider

from agent_toolbox.adapter.outbound.file.model.file_write_input import WriteFileInput
from agent_toolbox.adapter.outbound.file.model.file_write_output import WriteFileOutput
from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.vault import Vault

_TEXT_EXTENSIONS: frozenset[str] = frozenset({"md", "txt"})


class WriteFile(Tool[WriteFileInput, WriteFileOutput]):
    name = "file_writer"
    description = (
        "Write data to a file, replacing its contents. Supported formats: yml, yaml, json, "
        f"csv, md, txt. Current system: {sys.platform}."
    )
    input_model = WriteFileInput
    output_model = WriteFileOutput

    def __init__(
        self, file_handler_provider: FileHandlerProvider, vault: Vault | None = None
    ) -> None:
        self._file_handler_provider = file_handler_provider
        self._vault = vault
        if vault is not None:
            self.description = f"{self.description} Files are written to the vault: {vault.root}."

    async def run(self, arguments: WriteFileInput) -> WriteFileOutput:
        if not arguments.file_path.strip():
            raise ToolFailure("No file_path provided.")

        path: str = self._vault.resolve(arguments.file_path) if self._vault else arguments.file_path
        data: Any = _decoded(path, arguments.data)
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
    if not isinstance(data, str) or PurePath(file_path).suffix.lstrip(".") in _TEXT_EXTENSIONS:
        return data

    try:
        return orjson.loads(data)
    except orjson.JSONDecodeError as error:
        raise ToolFailure(f"Invalid JSON in data: {error}") from error

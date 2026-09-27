from typing import Any

from pydantic import BaseModel

from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.sandbox_run import SandboxRun


class StubFileHandler:
    def __init__(
        self,
        read_result: Any = None,
        read_error: Exception | None = None,
        write_error: Exception | None = None,
    ) -> None:
        self._read_result = read_result
        self._read_error = read_error
        self._write_error = write_error
        self.read_with: tuple[Any, ...] | None = None
        self.written: Any = None

    def read(self, read_chunk_mode: Any = None, start: Any = None, count: Any = None) -> Any:
        self.read_with = (read_chunk_mode, start, count)
        if self._read_error:
            raise self._read_error
        return self._read_result

    def write(self, data: Any) -> None:
        if self._write_error:
            raise self._write_error
        self.written = data


def file_handler_provider(handler: StubFileHandler):
    def provider(file_path: str) -> StubFileHandler:
        return handler

    return provider


class StubRepository:
    def __init__(self, rows: list[dict[str, Any]] | None = None, error: Exception | None = None):
        self._rows = rows or []
        self._error = error
        self.executed: list[str] = []

    async def execute(self, sql: str, parameters: Any = ()) -> list[dict[str, Any]]:
        if self._error:
            raise self._error
        self.executed.append(sql)
        return self._rows


class StubQueryHandler:
    def __init__(self, query: str, error: Exception | None = None) -> None:
        self._query = query
        self._error = error

    def transpile(self) -> str:
        if self._error:
            raise self._error
        return f"TRANSPILED {self._query}"


def query_factory(error: Exception | None = None):
    def factory(query: str, dialect: str = "sqlite") -> StubQueryHandler:
        return StubQueryHandler(query, error)

    return factory


class StubSandbox:
    def __init__(self, run: SandboxRun | None = None, error: str | None = None) -> None:
        self._run = run or SandboxRun(type_name="int", value=4)
        self._error = error
        self.codes: list[str] = []

    async def run(self, code: str) -> SandboxRun:
        self.codes.append(code)
        if self._error:
            raise ToolFailure(self._error)
        return self._run


class EchoInput(BaseModel):
    text: str
    times: int = 1


class EchoOutput(BaseModel):
    echoed: str


class Echo(Tool[EchoInput, EchoOutput]):
    name = "echo"
    description = "Repeat text."
    input_model = EchoInput
    output_model = EchoOutput

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    async def run(self, arguments: EchoInput) -> EchoOutput:
        if self._error:
            raise self._error
        return EchoOutput(echoed=arguments.text * arguments.times)

from agent_toolbox.adapter.outbound.code.model.python_execution_result import (
    PythonExecutionResult,
)
from agent_toolbox.adapter.outbound.file.model.file_read_result import FileReadResult
from agent_toolbox.adapter.outbound.file.model.file_write_result import FileWriteResult
from agent_toolbox.adapter.outbound.specification import (
    file_reader,
    file_writer,
    python_sandbox,
    user_database,
)
from agent_toolbox.adapter.outbound.sql.model.sql_query_result import SqlQueryResult


def test_python_sandbox_specification_declares_a_required_code_parameter() -> None:
    spec = python_sandbox.specification()

    assert spec.name == "python_executor"
    assert len(spec.parameters) == 1
    assert spec.parameters[0].name == "code"
    assert spec.parameters[0].required is True
    assert str(python_sandbox.TIMEOUT_SECONDS) in spec.description
    assert spec.output_type is PythonExecutionResult


def test_user_database_specification_declares_query_and_optional_dialect() -> None:
    spec = user_database.SPECIFICATION

    assert spec.name == "users_tables"
    names = {p.name: p.required for p in spec.parameters}
    assert names == {"query": True, "dialect": False}
    assert user_database.DIALECT in spec.description
    assert spec.output_type is SqlQueryResult


def test_file_reader_specification_declares_a_required_file_path_parameter() -> None:
    spec = file_reader.SPECIFICATION

    assert spec.name == "file_reader"
    file_path = next(p for p in spec.parameters if p.name == "file_path")
    assert file_path.required is True

    names = {p.name: p.required for p in spec.parameters}
    assert names == {"file_path": True, "start": False, "count": False}
    assert spec.output_type is FileReadResult


def test_file_writer_specification_declares_file_path_and_data_parameters() -> None:
    spec = file_writer.SPECIFICATION

    assert spec.name == "file_writer"
    names = {p.name: p.required for p in spec.parameters}
    assert names == {"file_path": True, "data": True}
    assert spec.output_type is FileWriteResult

from agent_toolbox.adapter.outbound.code.python_tool import ExecutePython
from agent_toolbox.application.catalog.tool_catalog import ToolCatalog
from agent_toolbox.domain.model.working_directory import WorkingDirectory
from bootstrap.di.sandbox_di import SandboxDI
from tests.agent_toolbox.stubs import Named


def test_python_tool_has_no_tool_functions_without_sandbox_tool_access(logger) -> None:
    tool: ExecutePython = SandboxDI(logger, None, tool_access=False).execute_python(ToolCatalog())

    assert "ToolError" not in tool.description


def test_python_tool_lists_the_tools_it_can_call_and_its_working_directory(
    logger, tmp_path
) -> None:
    sandbox = SandboxDI(logger, WorkingDirectory(str(tmp_path)), tool_access=True)

    tool: ExecutePython = sandbox.execute_python(ToolCatalog([Named("grafana_search")]))

    assert "Tools callable in code: grafana_search." in tool.description
    assert f"- Files: {tmp_path} is the code's current directory" in tool.description

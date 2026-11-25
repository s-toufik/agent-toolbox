from agent_toolbox.application.use_case.invoke_tool_usecase import InvokeToolUseCase
from agent_toolbox.domain.model.tool_scope import ToolScope

TOOL_NAMES = {"users_tables", "python_executor", "file_reader", "file_writer"}


def scope_named(di, name: str) -> ToolScope:
    return next(scope for scope in di._scopes.declared if scope.name == name)


async def test_use_case_serves_every_tool_and_connects_the_sqlite_repository(make_di) -> None:
    di = make_di()

    use_case = InvokeToolUseCase(await di._scope_tools(), di._logging)

    assert {tool.name for tool in use_case.tools} == TOOL_NAMES
    assert len(di._repositories) == 1
    assert await use_case.invoke("python_executor", {"code": "result = 1 + 1"}) == {
        "result_type": "int",
        "result": 2,
        "stdout": "",
    }

    await di._stop_factories()


async def test_a_scope_without_python_executor_in_its_tools_has_none(make_di, tmp_path) -> None:
    di = make_di(sandbox_tool_access=True, working_directory=tmp_path)

    observation = await di._scope_tools(scope_named(di, "observation"))
    everything = await di._scope_tools(scope_named(di, "all"))

    assert "python_executor" not in [tool.name for tool in observation.tools]
    assert observation.get("python_executor") is None
    assert everything.get("python_executor") is not None

    await di._stop_factories()


async def test_python_tool_lists_the_data_tools_with_sandbox_tool_access(make_di, tmp_path) -> None:
    di = make_di(sandbox_tool_access=True, working_directory=tmp_path)

    [python] = [tool for tool in (await di._scope_tools()).tools if tool.name == "python_executor"]

    assert "Tools callable in code: " in python.description
    assert "file_reader" in python.description
    assert "users_tables" in python.description
    assert f"- Files: {tmp_path} is the code's current directory" in python.description

    await di._stop_factories()


async def test_each_scope_that_lists_python_executor_has_its_own_describing_only_its_tools(
    make_di, tmp_path
) -> None:
    di = make_di(sandbox_tool_access=True, working_directory=tmp_path)

    coding = await di._scope_tools(scope_named(di, "coding"))
    kitchen = await di._scope_tools(scope_named(di, "kitchen"))

    assert [tool.name for tool in coding.tools] == ["python_executor", "file_reader", "file_writer"]
    assert [tool.name for tool in kitchen.tools] == ["python_executor"]
    [coding_python] = [tool for tool in coding.tools if tool.name == "python_executor"]
    [kitchen_python] = [tool for tool in kitchen.tools if tool.name == "python_executor"]
    assert "Tools callable in code: file_reader, file_writer." in coding_python.description
    assert "users_tables" not in coding_python.description
    assert "Tools callable in code" not in kitchen_python.description
    assert (
        await kitchen.get("python_executor").run(
            kitchen.get("python_executor").input_model(code="result = 6 * 7")
        )
        is not None
    )

    await di._stop_factories()


async def test_without_its_mcp_servers_the_kitchen_scope_boots_with_warnings(
    make_di, without_external_mcp, monkeypatch
) -> None:
    di = make_di()
    kitchen: ToolScope = scope_named(di, "kitchen")
    warnings: list[str] = []
    monkeypatch.setattr(di._logging, "warning", warnings.append)

    tools = await di._scope_tools(kitchen)

    assert [tool.name for tool in tools.tools] == ["python_executor"]
    assert len(warnings) == len(kitchen.aliases)

    await di._stop_factories()

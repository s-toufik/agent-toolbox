import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src"


MCP_SDK_EDGE = SOURCE / "bootstrap" / "application" / "mcp_sdk"
FRAMEWORKS = {"mcp", "starlette", "fastapi", "uvicorn", "granian"}
FRAMEWORK_TOOLKITS = ("pycraftcore.mcp_sdk", "pycraftcore.web_starlette")


def _modules(path: Path) -> set[str]:
    modules: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


def _imported_modules(package: str, outside: Path | None = None) -> dict[Path, set[str]]:
    return {
        path: _modules(path)
        for path in (SOURCE / package).rglob("*.py")
        if outside is None or not path.is_relative_to(outside)
    }


def _imported_roots(package: str) -> set[str]:
    return {
        module.split(".", 1)[0]
        for modules in _imported_modules(package).values()
        for module in modules
    }


def _toolkit(module: str) -> bool:
    return any(
        module == toolkit or module.startswith(f"{toolkit}.") for toolkit in FRAMEWORK_TOOLKITS
    )


def test_agent_toolbox_does_not_import_an_agent_package_directly() -> None:
    assert "agent" not in _imported_roots("agent_toolbox")


def test_agent_toolbox_does_not_import_langchain_or_langgraph() -> None:
    roots = _imported_roots("agent_toolbox")
    assert not roots & {"langchain", "langchain_core", "langchain_openai", "langgraph"}


def test_agent_toolbox_does_not_import_bootstrap() -> None:
    assert "bootstrap" not in _imported_roots("agent_toolbox")


def test_domain_layer_stays_free_of_frameworks() -> None:
    forbidden = {"fastapi", "starlette", "mcp", "langchain", "langgraph", "pydantic"}
    for path in (SOURCE / "agent_toolbox" / "domain").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.Import):
                module = node.names[0].name.split(".", 1)[0]
            elif isinstance(node, ast.ImportFrom) and node.module:
                module = node.module.split(".", 1)[0]
            assert module not in forbidden, f"{path} imports {module}"


def test_application_layer_does_not_import_transport_frameworks() -> None:
    assert not _imported_roots("agent_toolbox/application") & FRAMEWORKS


def test_agent_toolbox_reaches_mcp_only_through_pycraftcore_ports() -> None:
    for path, modules in _imported_modules("agent_toolbox").items():
        roots = {module.split(".", 1)[0] for module in modules}
        assert not roots & FRAMEWORKS, f"{path} imports {roots & FRAMEWORKS}"
        assert not {m for m in modules if _toolkit(m)}, f"{path} imports a framework toolkit"


def test_only_the_mcp_sdk_edge_of_bootstrap_imports_the_web_framework() -> None:
    for path, modules in _imported_modules("bootstrap", outside=MCP_SDK_EDGE).items():
        roots = {module.split(".", 1)[0] for module in modules}
        assert not roots & FRAMEWORKS, f"{path} imports {roots & FRAMEWORKS}"
        allowed = (
            {"pycraftcore.mcp_sdk"} if path.is_relative_to(SOURCE / "bootstrap" / "di") else set()
        )
        assert {m for m in modules if _toolkit(m)} <= allowed, f"{path} imports a framework toolkit"

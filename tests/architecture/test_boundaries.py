"""Keeps the toolbox's hexagon honest now that it's a standalone service.

`agent_toolbox` is reached only over MCP by whatever agent (or other MCP
client) is configured to use it -- it must never import an agent package
directly, must stay free of langchain/langgraph (that's the agent's
concern, not a tool server's), and its domain layer must stay
framework-free.
"""

import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src"


def _imported_roots(package: str) -> set[str]:
    roots: set[str] = set()
    for path in (SOURCE / package).rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots.add(node.module.split(".", 1)[0])
    return roots


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

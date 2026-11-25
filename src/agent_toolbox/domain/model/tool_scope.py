import builtins
import copy
import keyword
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from types import MappingProxyType
from typing import Any

ALL: str = "all"
_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
_CALLABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CATALOG_NAME = re.compile(r"[A-Za-z0-9_.-]+")
_SANDBOX_NAMES: frozenset[str] = frozenset(dir(builtins)) | {
    "ToolError",
    "WORKING_DIRECTORY",
    "result",
}


def _is_dunder(value: str) -> bool:
    return value.startswith("__") and value.endswith("__")


@dataclass(frozen=True, slots=True)
class ToolAlias:
    name: str
    target: str
    description: str | None = None
    fixed: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not _CALLABLE_NAME.fullmatch(self.name) or keyword.iskeyword(self.name):
            raise ValueError(
                f"tool alias name {self.name!r} must be a Python identifier that is not a "
                "keyword, so sandbox code can call it"
            )
        if self.name in _SANDBOX_NAMES or _is_dunder(self.name):
            raise ValueError(
                f"tool alias name {self.name!r} is already a name in the sandbox "
                "(a builtin, ToolError, WORKING_DIRECTORY or result)"
            )
        if not _CATALOG_NAME.fullmatch(self.target):
            raise ValueError(
                f"tool alias {self.name!r}: target {self.target!r} must be letters, digits, "
                "'_', '-' or '.'"
            )
        if self.description is not None and not self.description.strip():
            raise ValueError(f"tool alias {self.name!r}: description must not be blank")
        if any(not key.strip() for key in self.fixed):
            raise ValueError(f"tool alias {self.name!r}: fixed argument names must not be blank")
        object.__setattr__(self, "fixed", MappingProxyType(copy.deepcopy(dict(self.fixed))))


@dataclass(frozen=True, slots=True)
class ToolScope:
    name: str
    patterns: tuple[str, ...] = ()
    aliases: tuple[ToolAlias, ...] = ()

    def __post_init__(self) -> None:
        if not _NAME.match(self.name):
            raise ValueError(
                f"tool scope {self.name!r} must be lower case letters, digits, '-' or '_'"
            )
        if self.name == ALL and (self.patterns != ("*",) or self.aliases):
            raise ValueError(f"the {ALL!r} scope is built in: it holds every tool")
        if any(not pattern.strip() for pattern in self.patterns):
            raise ValueError(f"tool scope {self.name!r} has an empty pattern")
        self._check_aliases()

    @property
    def is_all(self) -> bool:
        return self.name == ALL

    def includes(self, tool_name: str) -> bool:
        return any(fnmatchcase(tool_name, pattern) for pattern in self.patterns)

    def alias(self, name: str) -> ToolAlias | None:
        return next((alias for alias in self.aliases if alias.name == name), None)

    def _check_aliases(self) -> None:
        names: list[str] = [alias.name for alias in self.aliases]
        self._refuse(
            "aliases named more than once", {name for name in names if names.count(name) > 1}
        )
        self._refuse(
            "aliases whose name a pattern also matches, a scope publishes one tool per name",
            {name for name in names if self.includes(name)},
        )
        renamed: set[str] = {alias.name for alias in self.aliases if alias.name != alias.target}
        self._refuse(
            "aliases built on another alias of the scope",
            {alias.name for alias in self.aliases if alias.target in renamed},
        )

    def _refuse(self, problem: str, names: set[str]) -> None:
        if names:
            raise ValueError(f"tool scope {self.name!r}: {problem}: {', '.join(sorted(names))}")


ALL_TOOLS: ToolScope = ToolScope(ALL, ("*",))

import re
from dataclasses import dataclass
from fnmatch import fnmatchcase

ALL: str = "all"
_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


@dataclass(frozen=True, slots=True)
class ToolScope:
    name: str
    patterns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _NAME.match(self.name):
            raise ValueError(
                f"tool scope {self.name!r} must be lower case letters, digits, '-' or '_'"
            )
        if self.name == ALL and self.patterns != ("*",):
            raise ValueError(f"the {ALL!r} scope is built in: it holds every tool")
        if any(not pattern.strip() for pattern in self.patterns):
            raise ValueError(f"tool scope {self.name!r} has an empty pattern")

    @property
    def is_all(self) -> bool:
        return self.name == ALL

    def includes(self, tool_name: str) -> bool:
        return any(fnmatchcase(tool_name, pattern) for pattern in self.patterns)


ALL_TOOLS: ToolScope = ToolScope(ALL, ("*",))

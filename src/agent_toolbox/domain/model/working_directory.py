import os
from dataclasses import dataclass

from agent_toolbox.domain.exception.tool_failure import ToolFailure


@dataclass(frozen=True, slots=True)
class WorkingDirectory:
    root: str

    def resolve(self, path: str) -> str:
        root: str = os.path.realpath(self.root)
        candidate: str = path if os.path.isabs(path) else os.path.join(root, path)
        resolved: str = os.path.realpath(candidate)

        if os.path.commonpath((os.path.normcase(resolved), os.path.normcase(root))) != (
            os.path.normcase(root)
        ):
            raise ToolFailure(f"Path {path!r} is outside the working directory.")

        return resolved

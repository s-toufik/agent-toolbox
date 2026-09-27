from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SandboxRun:
    type_name: str
    value: Any
    printed: str = ""

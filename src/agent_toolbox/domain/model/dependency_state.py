from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DependencyState:
    up: bool
    since: datetime
    error: str | None = None

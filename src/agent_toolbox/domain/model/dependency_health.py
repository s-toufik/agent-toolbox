from collections.abc import Callable
from datetime import UTC, datetime

from agent_toolbox.domain.model.dependency_state import DependencyState


class DependencyHealth:
    def __init__(self, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._clock = clock
        self._states: dict[str, DependencyState] = {}

    def up(self, name: str) -> bool:
        previous: DependencyState | None = self._states.get(name)
        if previous is not None and previous.up:
            return False
        self._states[name] = DependencyState(up=True, since=self._clock())
        return previous is not None

    def down(self, name: str, error: str) -> bool:
        previous: DependencyState | None = self._states.get(name)
        if previous is not None and not previous.up:
            self._states[name] = DependencyState(up=False, since=previous.since, error=error)
            return False
        self._states[name] = DependencyState(up=False, since=self._clock(), error=error)
        return True

    def is_up(self, name: str) -> bool:
        state: DependencyState | None = self._states.get(name)
        return state is not None and state.up

    @property
    def all_up(self) -> bool:
        return all(state.up for state in self._states.values())

    def snapshot(self) -> dict[str, DependencyState]:
        return dict(self._states)

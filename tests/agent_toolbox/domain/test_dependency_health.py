from datetime import UTC, datetime, timedelta

from agent_toolbox.domain.model.dependency_health import DependencyHealth


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def test_it_reports_only_the_moments_a_dependency_changes() -> None:
    clock = Clock()
    health = DependencyHealth(clock)

    assert health.up("grafana") is False
    assert health.down("grafana", "refused") is True
    clock.now += timedelta(seconds=30)
    assert health.down("grafana", "timeout") is False
    assert health.up("grafana") is True


def test_a_dependency_stays_down_since_it_first_failed_with_its_last_error() -> None:
    clock = Clock()
    health = DependencyHealth(clock)
    health.down("mongodb", "refused")
    first = clock.now
    clock.now += timedelta(minutes=2)
    health.down("mongodb", "timeout")

    state = health.snapshot()["mongodb"]

    assert (state.up, state.since, state.error) == (False, first, "timeout")
    assert health.all_up is False


def test_is_up_is_false_until_a_dependency_answered() -> None:
    health = DependencyHealth()

    assert health.is_up("grafana") is False
    health.up("grafana")
    assert health.is_up("grafana") is True
    health.down("grafana", "refused")
    assert health.is_up("grafana") is False

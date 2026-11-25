from datetime import timedelta

import pytest

from agent_toolbox.domain.model.token_lifetime import DEFAULT_TOKEN_LIFETIME, TokenLifetime


def test_a_token_lasts_five_hours_by_default() -> None:
    assert DEFAULT_TOKEN_LIFETIME.duration == timedelta(hours=5)


@pytest.mark.parametrize(
    ("expire", "duration"),
    [
        ("30m", timedelta(minutes=30)),
        ("12h", timedelta(hours=12)),
        ("7d", timedelta(days=7)),
        (" 2H ", timedelta(hours=2)),
        ("never", None),
        ("NEVER", None),
    ],
)
def test_expire_reads_never_or_a_number_of_minutes_hours_or_days(expire, duration) -> None:
    lifetime = TokenLifetime.parse(expire)

    assert lifetime.duration == duration


@pytest.mark.parametrize("expire", ["", "0h", "-1h", "5", "5 h", "1w", "1.5h", "forever"])
def test_an_expire_that_is_not_a_positive_duration_or_never_is_refused(expire) -> None:
    with pytest.raises(ValueError, match="must be 'never' or a positive number"):
        TokenLifetime.parse(expire)

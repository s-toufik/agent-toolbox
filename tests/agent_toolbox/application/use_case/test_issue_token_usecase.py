from datetime import timedelta

import pytest
from pycraftcore.jwt.adapter import PyJwtTokens

from agent_toolbox.application.use_case.issue_token_usecase import IssueTokenUseCase

TOKENS = PyJwtTokens("k" * 32)


def issue(username: str, expire: str | None = None, privileged: str | None = "toufik"):
    return IssueTokenUseCase(TOKENS, privileged).issue(username, expire)


def test_a_token_is_signed_for_its_username_and_lasts_five_hours() -> None:
    issued = issue("alice")

    claims = TOKENS.verify(issued.token)
    assert claims.subject == "alice"
    assert claims.expires_at - claims.issued_at == timedelta(hours=5)
    assert issued.lifetime.duration == timedelta(hours=5)


@pytest.mark.parametrize(("expire", "duration"), [("12h", timedelta(hours=12)), ("never", None)])
def test_jwt_username_chooses_its_token_s_lifetime(expire, duration) -> None:
    issued = issue("toufik", expire)

    assert issued.lifetime.duration == duration
    assert TOKENS.verify(issued.token).never_expires is (duration is None)


@pytest.mark.parametrize("privileged", ["toufik", None, ""])
def test_any_other_username_gets_five_hours_whatever_it_asks(privileged) -> None:
    issued = issue("alice", "never", privileged=privileged)

    assert issued.lifetime.duration == timedelta(hours=5)
    assert not TOKENS.verify(issued.token).never_expires


@pytest.mark.parametrize(
    ("username", "expire", "message"),
    [(" ", None, "needs a username"), ("toufik", "forever", "must be 'never' or a positive")],
)
def test_a_token_that_cannot_be_issued_is_refused(username, expire, message) -> None:
    with pytest.raises(ValueError, match=message):
        issue(username, expire)

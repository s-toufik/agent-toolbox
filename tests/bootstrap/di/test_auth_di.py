import pytest

from bootstrap.di.auth_di import AuthDI


@pytest.mark.parametrize("key", [None, ""])
def test_without_jwt_key_the_toolbox_cannot_check_tokens(key) -> None:
    with pytest.raises(ValueError, match="JWT_KEY is required"):
        _ = AuthDI(key, "toufik").tokens


def test_a_jwt_key_too_short_to_be_safe_is_refused() -> None:
    with pytest.raises(ValueError, match="at least 32 bytes"):
        _ = AuthDI("short", "toufik").tokens


def test_the_issued_tokens_are_the_ones_the_toolbox_checks() -> None:
    auth = AuthDI("k" * 32, "toufik")

    issued = auth.issue_token.issue("toufik", "never")

    assert auth.tokens.verify(issued.token).never_expires

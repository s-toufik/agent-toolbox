from dataclasses import dataclass

from pycraftcore.jwt import TokenIssuer

from agent_toolbox.domain.model.token_lifetime import DEFAULT_TOKEN_LIFETIME, TokenLifetime


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    lifetime: TokenLifetime


class IssueTokenUseCase:
    def __init__(self, issuer: TokenIssuer, privileged_username: str | None) -> None:
        self._issuer = issuer
        self._privileged_username = privileged_username

    def issue(self, username: str, expire: str | None = None) -> IssuedToken:
        if not username.strip():
            raise ValueError("a token needs a username")
        lifetime: TokenLifetime = DEFAULT_TOKEN_LIFETIME
        if expire is not None and self._chooses_its_lifetime(username):
            lifetime = TokenLifetime.parse(expire)
        return IssuedToken(self._issuer.issue(username, lifetime.duration), lifetime)

    def _chooses_its_lifetime(self, username: str) -> bool:
        return bool(self._privileged_username) and username == self._privileged_username

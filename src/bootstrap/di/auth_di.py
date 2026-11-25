from functools import cached_property

from pycraftcore.jwt.adapter import PyJwtTokens

from agent_toolbox.application.use_case.issue_token_usecase import IssueTokenUseCase


class AuthDI:
    def __init__(self, key: str | None, privileged_username: str | None) -> None:
        self._key = key
        self._privileged_username = privileged_username

    @cached_property
    def tokens(self) -> PyJwtTokens:
        if not self._key:
            raise ValueError("JWT_KEY is required: the toolbox signs and checks its tokens with it")
        return PyJwtTokens(self._key)

    @cached_property
    def issue_token(self) -> IssueTokenUseCase:
        return IssueTokenUseCase(self.tokens, self._privileged_username)

import pytest
from pycraftcore.jwt.adapter import PyJwtTokens
from starlette.applications import Starlette
from starlette.testclient import TestClient

from agent_toolbox.application.use_case.issue_token_usecase import IssueTokenUseCase
from bootstrap.application.mcp_sdk.token_route import TOKEN_PATH, token_route

TOKENS = PyJwtTokens("k" * 32)


def client() -> TestClient:
    return TestClient(Starlette(routes=[token_route(IssueTokenUseCase(TOKENS, "toufik"))]))


@pytest.mark.parametrize(
    ("body", "expires_in"),
    [
        ({"username": "alice"}, 18000),
        ({"username": "alice", "expire": "never"}, 18000),
        ({"username": "toufik", "expire": "30m"}, 1800),
        ({"username": "toufik", "expire": "never"}, None),
    ],
)
def test_the_endpoint_returns_a_bearer_token_and_its_lifetime(body, expires_in) -> None:
    response = client().post(TOKEN_PATH, json=body)

    assert response.status_code == 200
    answer = response.json()
    assert (answer["token_type"], answer["expires_in"]) == ("bearer", expires_in)
    assert TOKENS.verify(answer["access_token"]).subject == body["username"]


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ({}, "username: Field required"),
        ({"username": " "}, "a token needs a username"),
        ({"username": "toufik", "expire": "1w"}, "must be 'never' or a positive"),
    ],
)
def test_a_request_that_cannot_give_a_token_is_a_bad_request(body, detail) -> None:
    response = client().post(TOKEN_PATH, json=body)

    assert response.status_code == 400
    assert detail in response.json()["detail"]


def test_only_post_issues_tokens() -> None:
    assert client().get(TOKEN_PATH).status_code == 405

from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from agent_toolbox.application.use_case.issue_token_usecase import IssuedToken, IssueTokenUseCase

TOKEN_PATH: str = "/auth/token"


class TokenRequest(BaseModel):
    username: str
    expire: str | None = None


def token_route(issue_token: IssueTokenUseCase) -> Route:
    async def issue(request: Request) -> JSONResponse:
        try:
            asked: TokenRequest = TokenRequest.model_validate_json(await request.body())
            issued: IssuedToken = issue_token.issue(asked.username, asked.expire)
        except ValidationError as error:
            problems: str = "; ".join(
                f"{'.'.join(map(str, detail['loc']))}: {detail['msg']}" for detail in error.errors()
            )
            return JSONResponse({"detail": problems}, status_code=400)
        except ValueError as error:
            return JSONResponse({"detail": str(error)}, status_code=400)
        duration = issued.lifetime.duration
        return JSONResponse(
            {
                "access_token": issued.token,
                "token_type": "bearer",
                "expires_in": int(duration.total_seconds()) if duration is not None else None,
            }
        )

    return Route(TOKEN_PATH, issue, methods=["POST"])

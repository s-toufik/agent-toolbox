from typing import Any

from pydantic import BaseModel, Field


class QueryUsersOutput(BaseModel):
    rows: list[dict[str, Any]] = Field(
        description="Rows returned by the query, one object per row."
    )

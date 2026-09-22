from typing import Any

from pydantic import BaseModel, Field


class SqlQueryResult(BaseModel):
    rows: list[dict[str, Any]] = Field(description="Rows returned by the query, one dict per row.")

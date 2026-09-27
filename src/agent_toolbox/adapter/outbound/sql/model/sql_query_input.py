from pydantic import BaseModel, Field

DEFAULT_DIALECT: str = "sqlite"


class QueryUsersInput(BaseModel):
    query: str = Field(description="SQL query to execute.")
    dialect: str = Field(default=DEFAULT_DIALECT, description="sqlglot source dialect.")

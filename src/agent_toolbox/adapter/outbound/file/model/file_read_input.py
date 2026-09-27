from pydantic import BaseModel, Field


class ReadFileInput(BaseModel):
    file_path: str = Field(
        description="File path, including extension. When a vault is configured, relative paths resolve inside it and paths outside it are refused."
    )
    start: int | None = Field(
        default=None,
        description="Line number to start reading from (0-based). Giving start or count reads raw lines.",
    )
    count: int | None = Field(default=None, description="Maximum number of lines to read.")

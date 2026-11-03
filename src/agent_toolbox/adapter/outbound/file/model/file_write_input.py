from typing import Any

from pydantic import BaseModel, Field


class WriteFileInput(BaseModel):
    file_path: str = Field(
        description="File path, including extension. When a working directory is configured, relative paths resolve inside it and paths outside it are refused."
    )
    data: dict[str, Any] | list[dict[str, Any]] | str = Field(
        description=(
            "What to write: an object for json/yml/yaml, a list of row objects for csv, "
            "a string for md/txt. Plain JSON values only."
        )
    )

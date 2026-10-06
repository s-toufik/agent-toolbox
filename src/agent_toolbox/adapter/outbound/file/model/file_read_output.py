from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class TextContent(BaseModel):
    format: Literal["text"] = "text"
    text: str = Field(description="Raw file contents (md, txt, svg).")


class StructuredContent(BaseModel):
    format: Literal["structured"] = "structured"
    data: dict[str, Any] | list[Any] = Field(description="Parsed document (json, yml, yaml).")


class RowsContent(BaseModel):
    format: Literal["rows"] = "rows"
    rows: list[dict[str, Any]] = Field(description="Parsed CSV rows.")


class LinesContent(BaseModel):
    format: Literal["lines"] = "lines"
    lines: list[str] = Field(description="The requested lines, in order.")


class ReadFileOutput(BaseModel):
    path: str
    content: Annotated[
        TextContent | StructuredContent | RowsContent | LinesContent,
        Field(discriminator="format"),
    ]

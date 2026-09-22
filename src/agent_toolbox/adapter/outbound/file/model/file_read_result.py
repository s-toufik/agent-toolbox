from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class TextFileResult(BaseModel):
    format: Literal["text"] = "text"
    path: str
    text: str = Field(description="Raw file contents (txt, md).")


class StructuredFileResult(BaseModel):
    format: Literal["structured"] = "structured"
    path: str
    data: dict[str, Any] = Field(description="Parsed document (json, yml/yaml).")


class RowsFileResult(BaseModel):
    format: Literal["rows"] = "rows"
    path: str
    rows: list[dict[str, Any]] = Field(description="Parsed CSV rows.")


class LinesFileResult(BaseModel):
    format: Literal["lines"] = "lines"
    path: str
    lines: list[str] = Field(
        description="Requested line range, one entry per line, in the order read."
    )


type FileReadResult = Annotated[
    TextFileResult | StructuredFileResult | RowsFileResult | LinesFileResult,
    Field(discriminator="format"),
]

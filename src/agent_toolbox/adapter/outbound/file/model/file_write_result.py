from pydantic import BaseModel, Field


class FileWriteResult(BaseModel):
    path: str = Field(description="Absolute path the data was written to.")
